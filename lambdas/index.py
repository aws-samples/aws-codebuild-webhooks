"""
CodeBuild status webhook notifier

This Lambda is invoked in response to CodeBuild status changes. A list of interested hooks
is obtained from DynamoDB using the build project name and a customisable message will
be posted to each
"""
import os
import logging
import json
from string import Template
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
import requests

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))
dynamodb = boto3.resource("dynamodb")
ssm = boto3.client("ssm")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def lambda_handler(event, context):
    logger.info(event)
    project = event["detail"]["project-name"]
    status = event["detail"]["build-status"]
    env_vars = event["detail"]["additional-information"]["environment"]["environment-variables"]

    template_params = {
        "PROJECT": project,
        "STATUS": status,
    }

    template_params.update({i["name"]: i["value"] for i in env_vars})
    logger.info("Template params: %s", template_params)

    hooks = get_hooks_for_project(project)
    logger.info("Obtained %s hooks for project %s", len(hooks), project)
    for i in hooks:
        try:
            hook_url_param = i["hook_url_param_name"]
            statuses = i["statuses"]
            message = compile_template(template_params, i.get("template"))
            logger.info("Compiled template: %s", message)
            if status in statuses:
                logger.info("Invoking hook with SSM param '%s' for status '%s'", hook_url_param, status)
                hook_url = get_ssm_param(hook_url_param)
                headers = None
                header_param_name = i.get("hook_headers_param_name", None)
                if header_param_name:
                    headers = json.loads(get_ssm_param(header_param_name))
                invoke_webhook(hook_url, message, headers)
        except ClientError as e:
            logger.error(
                "Unable to retrieve webhook url from Parameter Store for item %s",
                hook_url_param)
            logger.error(str(e))
        except ValueError as e:
            logger.error(
                "Unable to post to webhook url from Parameter Store for item %s",
                hook_url_param)
            logger.error(str(e))
        except KeyError as e:
            logger.error("Invalid DDB item. Verify your template is valid.")
            logger.error(str(e))


def get_hooks_for_project(project):
    response = table.query(
        KeyConditionExpression=Key("project").eq(project)
    )

    return response["Items"]


def get_ssm_param(param_name):
    response = ssm.get_parameter(
        Name=param_name,
        WithDecryption=True
    )

    return response["Parameter"]["Value"]


def invoke_webhook(webhook_url, payload, additional_headers=None):
    headers = {'Content-Type': 'application/json'}
    if additional_headers:
        headers.update(additional_headers)
    response = requests.post(
        webhook_url, data=payload,
        headers=headers
    )
    if response.status_code != 200:
        raise ValueError(
            'Webhook returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )


def compile_template(template_params, template=None):
    if not template:
        template = '{"text": "Build of *$PROJECT* reached status *$STATUS*"}'
    if not template_params:
        template_params = {}

    t = Template(template)

    return t.substitute(template_params)
