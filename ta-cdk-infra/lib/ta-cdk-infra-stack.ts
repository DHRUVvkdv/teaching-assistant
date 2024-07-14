import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as fs from 'fs';
import * as path from 'path';
import { AttributeType, BillingMode, Table } from "aws-cdk-lib/aws-dynamodb";
import {
  DockerImageFunction,
  DockerImageCode,
  FunctionUrlAuthType,
  Architecture,
} from "aws-cdk-lib/aws-lambda";
import { ManagedPolicy } from "aws-cdk-lib/aws-iam";
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as dotenv from 'dotenv';
dotenv.config({ path: '../image/.env' });

export class TaCdkInfraStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Get the environment variables from the Python config file.
    const pineconeApiKey = process.env.PINECONE_API_KEY;
    if (!pineconeApiKey) {
      throw new Error("PINECONE_API_KEY environment variable is not set");
    }
    const apiKey = process.env.API_KEY;
    if (!apiKey) {
      throw new Error("API_KEY environment variable is not set");
    }

    // Create a DynamoDB table to store the query data and results.
    const teachingAssistantTavilyQueryTable = new Table(this, "QueriesTable", {
      tableName: "teaching-assistant-tavily-queries-table",  // Set the table name as requested
      partitionKey: { name: "query_id", type: AttributeType.STRING },
      billingMode: BillingMode.PAY_PER_REQUEST,
    });

    // Create a new DynamoDB table for processed files
    const processedFilesTable = new Table(this, "ProcessedFilesTable", {
      tableName: "teaching-assistant-tavily-processed-files",
      partitionKey: { name: "filename", type: AttributeType.STRING },
      billingMode: BillingMode.PAY_PER_REQUEST,
    });

    // Function to handle the API requests. Uses same base image, but different handler.
    const apiImageCode = DockerImageCode.fromImageAsset("../image", {
      cmd: ["main.handler"]
    });
    const apiFunction = new DockerImageFunction(this, "ApiFunc", {
      code: apiImageCode,
      memorySize: 256,
      timeout: cdk.Duration.seconds(30),
      architecture: Architecture.ARM_64,
      environment: {
        TABLE_NAME: teachingAssistantTavilyQueryTable.tableName,
        PINECONE_API_KEY: pineconeApiKey,
        API_KEY: apiKey,
        S3_BUCKET: 'teaching-assistant-tavily',  // Added S3_BUCKET environment variable
        PROCESSED_FILES_TABLE: processedFilesTable.tableName,  // Added PROCESSED_FILES_TABLE environment variable
      },
    });

    // Grant Bedrock permissions to the API function
    apiFunction.role?.addManagedPolicy(
      ManagedPolicy.fromAwsManagedPolicyName("AmazonBedrockFullAccess")
    );

    // Public URL for the API function.
    const functionUrl = apiFunction.addFunctionUrl({
      authType: FunctionUrlAuthType.NONE,
    });

    // Reference the existing S3 bucket
    const existingBucket = s3.Bucket.fromBucketName(this, 'ExistingBucket', 'teaching-assistant-tavily');

    // Grant read/write permissions to the API function
    existingBucket.grantReadWrite(apiFunction);

    // Grant S3 full access to the API function
    apiFunction.role?.addManagedPolicy(
      ManagedPolicy.fromAwsManagedPolicyName("AmazonS3FullAccess")
    );
    
    // Grant permissions for all resources to work together.
    teachingAssistantTavilyQueryTable.grantReadWriteData(apiFunction);
    processedFilesTable.grantReadWriteData(apiFunction);

    // Output the URL for the API function.
    new cdk.CfnOutput(this, "FunctionUrl", {
      value: functionUrl.url,
    });
  }
}