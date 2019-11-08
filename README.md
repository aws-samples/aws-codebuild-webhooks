# CodeBuild Webhooks

A solution for CodeBuild custom webhook notifications

## Deployment

Deploy using CloudFormation via the CLI

```
CFN_BUCKET=your-temp-bucket
SSM_KEY=$(aws kms describe-key --key-id alias/aws/ssm --query KeyMetadata.KeyId --output text)
virtualenv venv
source venv/bin/activate
pip install -r prod.txt -t lambdas/
aws cloudformation package --output-template-file packaged.yaml --template-file template.yaml --s3-bucket $CFN_BUCKET 
aws cloudformation deploy \
  --stack-name codebuild-webhooks \
  --template-file packaged.yaml \
  --parameter-overrides SSMKeyId=$SSM_KEY \
  --capabilities CAPABILITY_IAM
```

## Registering a Webhook
To register a webhook, you need to create a new item in the DDB table with the following keys:

- `project`: The name of the CodeBuild project for which your webhook should be invoked 
- `hook_url_param_name`: The name of the SSM parameter which contains the URL for your webhook. The
param name must be prefixed with `/webhooks/`
- `statuses`: The list of CodeBuild statuses which your webhook should respond to
- `template` (optional): A template for the body of the request that will be made to your webhook.
This should be a properly escaped JSON string. The `$PROJECT` and `$STATUS` placeholders can be used
in your template which will be substituted at runtime. Additionally, any env vars on your CodeBuild
job are available in your template by prefixing their name with `$`.
- `hook_headers_param_name` (optional): The name of the SSM parameter which contains a 
JSON string containing key/value pairs for custom headers for your webhooks. This can be used
for things such as Authorization headers. The param name must be prefixed with `webhooks/`

### Example 1: Creating a simple Slack channel webhook
1. Follow [Slack's Incoming Webhook Instructions] to create a webhook
2. Create a parameter in SSM containing the Webhook URL generated for you by Slack:
    ```
    aws ssm put-parameter --cli-input-json '{
      "Name": "/webhooks/your-slack-webhook-url",
      "Value": "url-from-slack",
      "Type": "SecureString",
      "Description": "Slack webhook URL for my project"
    }'
    ```
3. Create an entry in the DDB webhooks table which uses the default template:
    ```
    aws dynamodb put-item --table-name CodeBuildWebhooks --item file://examples/slack_simple.json
     ```

### Example 2: Creating a customised Slack channel webhook 
The steps are the same as in [Example 1](#creating-a-simple-slack-channel-webhook) except you
need to provide a custom template when registering the webhook in DDB. This example also makes use
of Slack's flavour of markdown. Once you've substituted the relevant values in `examples/slack_custom.json`,
run the following command:
```
aws dynamodb put-item --table-name CodeBuildWebhooks --item file://examples/slack_custom.json
```

You could also use [Slack Blocks](https://api.slack.com/block-kit) in your template and any
environment variables from your CodeBuild job will be available for interpolation in your template.

### Example 3: Creating a Jira Issues webhook
1. Follow [Jira's Auth Instructions] to obtain a basic auth header
2. Create a parameter in SSM containing the Jira Issues API endpoint for your Jira instance:
    ```
    aws ssm put-parameter --cli-input-json '{
     "Name": "/webhooks/jira-issues-webhook-url",
     "Value": "https://<my-jira-server>/rest/api/latest/issue/",
     "Type": "String",
     "Description": "Jira issues Rest API URL"
    }'
    ```
3. Create a parameter in SSM containing your basic auth headers as a JSON string:
    ```
    aws ssm put-parameter --cli-input-json '{
     "Name": "/webhooks/jira-basic-auth-headers",
     "Value": "{\"Authorization\": \"Basic <base64 encoded useremail:api_token>\"}",
     "Type": "SecureString",
     "Description": "Jira basic auth headers for CodeBuild webhooks"
    }
    ```
4. Create an entry in the DDB webhooks table which uses the default template, substituting values
as required:
    ```
    aws dynamodb put-item --table-name CodeBuildWebhooks --item file://examples/jira.json
    ```

## Tests
To execute tests, run:
```
python -m unittest discover tests
```

[Slack's Incoming Webhook Instructions]: https://slack.com/intl/en-gb/help/articles/115005265063
[Jira's Auth Instructions]: https://developer.atlassian.com/cloud/jira/platform/jira-rest-api-basic-authentication/#supplying-basic-auth-headers

## Contributing

Contributions are more than welcome. Please read the [code of conduct](CODE_OF_CONDUCT.md) and the [contributing guidelines](CONTRIBUTING.md).

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
