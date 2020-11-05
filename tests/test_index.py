"""
Lambda tests
"""
import unittest
import os
from mock import patch, ANY, Mock
with patch.dict(os.environ, {'TABLE_NAME':'mytemp', 'AWS_DEFAULT_REGION': 'eu-west-1'}):
    from lambdas import index


class TestHandler(unittest.TestCase):
    @patch("lambdas.index.get_hooks_for_project")
    @patch("lambdas.index.get_ssm_param")
    @patch("lambdas.index.invoke_webhook")
    @patch("lambdas.index.compile_template")
    def test_it_handles_standard_build_event(self, compile_template, invoke_webhook, get_ssm_param, get_hooks_for_project):
        get_hooks_for_project.return_value = [{"hook_url_param_name": "some_val", "statuses": ["SUCCEEDED"]}]
        get_ssm_param.return_value = "hook_url"
        index.lambda_handler(get_build_event(), {})
        compile_template.assert_called_with({'PROJECT': 'my-sample-project', 'STATUS': 'SUCCEEDED'}, None)
        invoke_webhook.assert_called_with("hook_url", ANY, None)

    @patch("lambdas.index.get_hooks_for_project")
    @patch("lambdas.index.get_ssm_param")
    @patch("lambdas.index.invoke_webhook")
    @patch("lambdas.index.compile_template")
    def test_it_handles_custom_headers(self, compile_template, invoke_webhook, get_ssm_param, get_hooks_for_project):
        get_hooks_for_project.return_value = [{"hook_headers_param_name": "some_val", "hook_url_param_name": "some_other_val", "statuses": ["SUCCEEDED"]}]
        get_ssm_param.side_effect = ["hook_url", '{"Authorization": "Bearer abc123"}']
        index.lambda_handler(get_build_event(), {})
        compile_template.assert_called_with({'PROJECT': 'my-sample-project', 'STATUS': 'SUCCEEDED'}, None)
        invoke_webhook.assert_called_with("hook_url", ANY, {"Authorization": "Bearer abc123"})


class TestTemplater(unittest.TestCase):
    template_params = {
        "PROJECT": "test",
        "VERSION": 1,
        "STATUS": "SUCCEEDED",
    }

    def test_it_compiles_valid_templates(self):
        expected = "Some custom message including test and 1"
        actual = index.compile_template(self.template_params, "Some custom message including $PROJECT and $VERSION")
        self.assertEqual(expected, actual)

    def test_it_provides_default_template(self):
        expected = '{"text": "Build of *test* reached status *SUCCEEDED*"}'
        actual = index.compile_template(self.template_params)
        self.assertEqual(expected, actual)

    def test_it_throws_for_invalid_templates(self):
        self.assertRaises(KeyError, index.compile_template, self.template_params, "$invalid $vars $specified")


class TestHooks(unittest.TestCase):
    @patch("lambdas.index.ssm")
    def test_it_retrieves_hook_details_from_ssm(self, mock_ssm):
        expected = "test"
        mock_ssm.get_parameter.return_value = {"Parameter": {"Value": expected}}
        actual = index.get_ssm_param("my_param")
        self.assertEqual(expected, actual)

    @patch("lambdas.index.table")
    def test_it_retrieves_hooks_from_dynamodb(self, mock_table):
        expected = ["foo"]
        mock_table.query.return_value = {"Items": expected}
        actual = index.get_hooks_for_project("my_project")
        self.assertEqual(expected, actual)

    @patch("lambdas.index.requests")
    def test_it_invokes_webhook_correctly(self, mock_request):
        webhook_url = "https://example.com"
        payload = "something"
        mock_request.post.return_value = Mock(status_code=200)
        index.invoke_webhook(webhook_url, payload)
        mock_request.post.assert_called_with(
            webhook_url, data=payload,
            headers={'Content-Type': 'application/json'}
        )

    @patch("lambdas.index.requests")
    def test_it_throws_on_non_200_response(self, mock_request):
        webhook_url = "https://example.com"
        payload = "something"
        mock_request.post.return_value = Mock(status_code=401)
        self.assertRaises(ValueError, index.invoke_webhook, webhook_url, payload)


def get_build_event():
    return {
        "version": "0",
        "id": "c030038d-8c4d-6141-9545-00ff7b7153EX",
        "detail-type": "CodeBuild Build State Change",
        "source": "aws.codebuild",
        "account": "account-id",
        "time": "2017-09-01T16:14:28Z",
        "region": "us-west-2",
        "resources": [
            "arn:aws:codebuild:us-west-2:account-id:build/my-sample-project:8745a7a9-c340-456a-9166-edf953571bEX"
        ],
        "detail": {
            "build-status": "SUCCEEDED",
            "project-name": "my-sample-project",
            "build-id": "arn:aws:codebuild:us-west-2:account-id:build/my-sample-project:8745a7a9-c340-456a-9166-edf953571bEX",
            "additional-information": {
                "artifact": {
                    "md5sum": "da9c44c8a9a3cd4b443126e823168fEX",
                    "sha256sum": "6ccc2ae1df9d155ba83c597051611c42d60e09c6329dcb14a312cecc0a8e39EX",
                    "location": "arn:aws:s3:::codebuild-account-id-output-bucket/my-output-artifact.zip"
                },
                "environment": {
                    "image": "aws/codebuild/standard:2.0",
                    "privileged-mode": False,
                    "compute-type": "BUILD_GENERAL1_SMALL",
                    "type": "LINUX_CONTAINER",
                    "environment-variables": []
                },
                "timeout-in-minutes": 60,
                "build-complete": True,
                "initiator": "MyCodeBuildDemoUser",
                "build-start-time": "Sep 1, 2017 4:12:29 PM",
                "source": {
                    "location": "codebuild-account-id-input-bucket/my-input-artifact.zip",
                    "type": "S3"
                },
                "logs": {
                    "group-name": "/aws/codebuild/my-sample-project",
                    "stream-name": "8745a7a9-c340-456a-9166-edf953571bEX",
                    "deep-link": "https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#logEvent:group=/aws/codebuild/my-sample-project;stream=8745a7a9-c340-456a-9166-edf953571bEX"
                },
                "phases": [
                    {
                        "phase-context": [],
                        "start-time": "Sep 1, 2017 4:12:29 PM",
                        "end-time": "Sep 1, 2017 4:12:29 PM",
                        "duration-in-seconds": 0,
                        "phase-type": "SUBMITTED",
                        "phase-status": "SUCCEEDED"
                    },
                    {
                        "phase-context": [],
                        "start-time": "Sep 1, 2017 4:12:29 PM",
                        "end-time": "Sep 1, 2017 4:13:05 PM",
                        "duration-in-seconds": 36,
                        "phase-type": "PROVISIONING",
                        "phase-status": "SUCCEEDED"
                    },
                    {
                        "phase-context": [],
                        "start-time": "Sep 1, 2017 4:13:05 PM",
                        "end-time": "Sep 1, 2017 4:13:10 PM",
                        "duration-in-seconds": 4,
                        "phase-type": "DOWNLOAD_SOURCE",
                        "phase-status": "SUCCEEDED"
                    },
                    {
                        "phase-context": [],
                        "start-time": "Sep 1, 2017 4:13:10 PM",
                        "end-time": "Sep 1, 2017 4:13:10 PM",
                        "duration-in-seconds": 0,
                        "phase-type": "INSTALL",
                        "phase-status": "SUCCEEDED"
                    },
                    {
                        "phase-context": [],
                        "start-time": "Sep 1, 2017 4:13:10 PM",
                        "end-time": "Sep 1, 2017 4:13:10 PM",
                        "duration-in-seconds": 0,
                        "phase-type": "PRE_BUILD",
                        "phase-status": "SUCCEEDED"
                    },
                    {
                        "phase-context": [],
                        "start-time": "Sep 1, 2017 4:13:10 PM",
                        "end-time": "Sep 1, 2017 4:14:21 PM",
                        "duration-in-seconds": 70,
                        "phase-type": "BUILD",
                        "phase-status": "SUCCEEDED"
                    },
                    {
                        "phase-context": [],
                        "start-time": "Sep 1, 2017 4:14:21 PM",
                        "end-time": "Sep 1, 2017 4:14:21 PM",
                        "duration-in-seconds": 0,
                        "phase-type": "POST_BUILD",
                        "phase-status": "SUCCEEDED"
                    },
                    {
                        "phase-context": [],
                        "start-time": "Sep 1, 2017 4:14:21 PM",
                        "end-time": "Sep 1, 2017 4:14:21 PM",
                        "duration-in-seconds": 0,
                        "phase-type": "UPLOAD_ARTIFACTS",
                        "phase-status": "SUCCEEDED"
                    },
                    {
                        "phase-context": [],
                        "start-time": "Sep 1, 2017 4:14:21 PM",
                        "end-time": "Sep 1, 2017 4:14:26 PM",
                        "duration-in-seconds": 4,
                        "phase-type": "FINALIZING",
                        "phase-status": "SUCCEEDED"
                    },
                    {
                        "start-time": "Sep 1, 2017 4:14:26 PM",
                        "phase-type": "COMPLETED"
                    }
                ]
            },
            "current-phase": "COMPLETED",
            "current-phase-context": "[]",
            "version": "1"
        }
    }
