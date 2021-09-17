# forward-kitchens

This project contains source code and supporting files for a serverless application that you can deploy with the SAM CLI. It includes the following files and folders.

- orders - Code for the application's Lambda function.
- tests - Tests for the application code. 
- template.yaml - A template that defines the application's AWS resources.

The application uses several AWS resources, including Lambda functions and an API Gateway API. These resources are defined in the `template.yaml` file in this project. You can update the template to add AWS resources through the same deployment process that updates your application code.

## Architecture

The app consist of two Lambdas, one DynamoDB table and one API Gateway.

- CreateOrderFunction lambda validates and creates items in the Orders table.
- ListOrdersFunction lambda responses with the list of active orders, as per requirements.
- Orders table uses `orderId` as the primary key to avoid conflicts. It specifies TTL attribute for AWS to eventually (and free for us) remove expired orders. List lookups are done in a tricky manner using a separate index to avoid Scan requests: we are using the beginning of each hour as the primary key and querying all items for a set of hours. Yes, it means we're doing from 1 to 3 query requests per one listing request, but it will save us throughput in the case of many orders.

### TODO

- add authentication layer
- optionally add pagination to the listing API

## Deploy the application

The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda. It can also emulate your application's build environment and API.

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

Optionally, you may want to use [virualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/).

To build and deploy your application for the first time, run the following in your shell:

```bash
make deploy
```

The command will build and deploy the application to AWS, with a series of prompts:

* **Stack Name**: The name of the stack to deploy to CloudFormation. This should be unique to your account and region, and a good starting point would be something matching your project name.
* **AWS Region**: The AWS region you want to deploy your app to.
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates, including this example, create AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modifies IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.

You can find your API Gateway Endpoint URL in the output values displayed after deployment.

## Use the SAM CLI to build and test locally

Build your application with the `sam build --use-container` command.

```bash
forward-kitchens$ sam build --use-container
```

The SAM CLI installs dependencies defined in `orders/requirements.txt`, creates a deployment package, and saves it in the `.aws-sam/build` folder.

Test a single function by invoking it directly with a test event. An event is a JSON document that represents the input that the function receives from the event source. Test events are included in the `events` folder in this project.

The SAM CLI can also emulate your application's API. Use the `sam local start-api` to run the API locally on port 3000.

```bash
forward-kitchens$ sam local start-api
forward-kitchens$ curl http://localhost:3000/
```

## Tests

Tests are defined in the `tests` folder in this project.

```bash
forward-kitchens$ make test
```

## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
aws cloudformation delete-stack --stack-name forward-kitchens
```
