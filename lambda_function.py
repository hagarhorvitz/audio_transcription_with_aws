# The code in this file is a Lambda function #

import os         
import json            
import boto3 
import urllib.parse 

s3 = boto3.client("s3") 
bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("REGION","eu-central-1"))

MODEL_ID = os.environ["MODEL_ID"]
INPUT_BUCKET = os.environ["INPUT_BUCKET"] 
DEFAULT_TRANSCRIPT_OBJECT_KEY = os.environ["DEFAULT_TRANSCRIPT_OBJECT_KEY"] 
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET", INPUT_BUCKET) 
OUTPUT_OBJECT_KEY = os.environ.get("OUTPUT_OBJECT_KEY", "")
OUTPUT_PREFIX = os.environ.get("OUTPUT_PREFIX", "") 


def _get_input_from_event(event):
    if isinstance(event, dict) and event.get("Records"):
        record = event["Records"][0]
        in_bucket = record["s3"]["bucket"]["name"]
        input_key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        return in_bucket, input_key
    return INPUT_BUCKET, DEFAULT_TRANSCRIPT_OBJECT_KEY


def _get_output(event, in_bucket, input_key):
    out_bucket = OUTPUT_BUCKET
    out_object_key = OUTPUT_OBJECT_KEY

    if isinstance(event, dict):
        out_bucket = event.get("output_bucket", out_bucket)
        out_object_key = event.get("output_object_key", out_object_key)

    if not out_object_key:
        base = os.path.splitext(os.path.basename(input_key))[0]
        folder = OUTPUT_PREFIX or os.path.dirname(input_key)
        out_object_key = f"{folder.rstrip('/')}/{base}.summary.json" if folder else f"{base}.summary.json"

    out_bucket = out_bucket or in_bucket
    return out_bucket, out_object_key


def lambda_handler(event, context):
    input_bucket, input_obj_key = _get_input_from_event(event)

    obj = s3.get_object(Bucket=input_bucket, Key=input_obj_key)
    transcribe_json = json.loads(obj["Body"].read()) 
    transcript_text = transcribe_json["results"]["transcripts"][0]["transcript"]

    prompt = "סכם את השיחה בשלוש נקודות בעברית תקנית."
    user_msg = f"{prompt}\n\nטקסט:\n{transcript_text}" 

    payload = {
        "anthropic_version": "bedrock-2023-05-31",      
        "max_tokens": 400, 
        "messages": [    
            {"role": "user", "content": [{"type": "text", "text": user_msg}]}
        ]
    }

    response = bedrock.invoke_model(                       
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload).encode("utf-8")
    )

    body = json.loads(response["body"].read().decode("utf-8"))  
    summary_text = body["content"][0]["text"] 

    output_bucket, output_obj_key = _get_output(event, input_bucket, input_obj_key)
    output_doc = {"job": input_obj_key, "model": MODEL_ID, "prompt": prompt, "summary": summary_text}
    s3.put_object(         
        Bucket=output_bucket,
        Key=output_obj_key,
        Body=json.dumps(output_doc, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json; charset=utf-8"
    )

    return {
        "status": "ok", 
        "default_env_variables": f"INPUT_BUCKET: {INPUT_BUCKET}/ DEFAULT_TRANSCRIPT_OBJECT_KEY: {DEFAULT_TRANSCRIPT_OBJECT_KEY}/ OUTPUT_OBJECT_KEY: {OUTPUT_OBJECT_KEY}/ OUTPUT_PREFIX: {OUTPUT_PREFIX}",
        "input_s3_uri": f"input_bucket: {input_bucket}/ input_obj_key: {input_obj_key}",
        "output_s3_uri": f"output_bucket: {output_bucket}/ output_obj_key: {output_obj_key}"
        }
