# Audio Transcribe by AWS services

## S3 → Transcribe → Lambda Function (S3 Trigger) → Bedrock → S3

This project is a small, compact, production‑ready serverless pipeline that turns speech into clear, actionable notes. 
A short audio file is transcribed by **Amazon Transcribe**; when the transcript JSON lands in S3 it automatically triggers a Python **AWS Lambda** function.
The Lambda calls **Amazon Bedrock (Anthropic Claude 3 Haiku)** to produce a clean Hebrew summary and then writes the result back to **Amazon S3** as UTF‑8 JSON.
In one line: **audio → transcript → summary → JSON in S3** - simple, repeatable, and easy to extend.

---


## Architecture

```
S3 (Transcribe JSON)
        │  (ObjectCreated: *.json)
        ▼
Lambda: summarize-transcript-bedrock
        │  Reads transcript text → calls Bedrock Claude → builds JSON
        ▼
S3 (output bucket) transcript-summaries/<job-name>.summary.json
```

## AWS Resources (Region & Names)

* **Region:** `eu-central-1` (Frankfurt)
* **Lambda function:** `summarize-transcript-bedrock`
* **Bedrock model:** `anthropic.claude-3-haiku-20240307-v1:0`
* **S3 input default bucket:** `my-audio-transaction-bucket` (holds Transcribe output JSON under `audio-transcript/`, and holds the audio files under `audio-and-records/`)
* **S3 output default bucket:** `output-audio-transcripts-bucket` (stores summary JSON under `transcript-summaries/`)

> Separate input/output buckets avoid accidental trigger loops (suggested by AWS)


## Deployment

1. **S3 buckets**
    * Create (if missing) the two buckets listed above and the prefixes:

* Input: `audio-transcript/`
* Output: `transcript-summaries/`

2. **Set IAM role for Lambda**
   Attach CloudWatch Logs permissions (e.g., `AWSLambdaBasicExecutionRole`) and a minimal custom inline policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "bedrock:InvokeModel",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:bedrock:eu-central-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
                "arn:aws:s3:::my-audio-transaction-bucket/*",
                "arn:aws:s3:::output-audio-transcripts-bucket/*",
                "arn:aws:s3:::my-audio-transaction-bucket",
                "arn:aws:s3:::output-audio-transcripts-bucket"
            ]
        }
    ]
}
```

### Environment Variables

Use the console to set these on the Lambda (the `.env` is only a reference):

```dotenv
    INPUT_BUCKET="my-audio-transaction-bucket"
    MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0"
    REGION="eu-central-1"
    DEFAULT_TRANSCRIPT_OBJECT_KEY="audio-transcript/my-audio.json"
    OUTPUT_BUCKET="output-audio-transcripts-bucket"
    OUTPUT_OBJECT_KEY=""
    OUTPUT_PREFIX="transcript-summaries/"
```

Notes:
* If `OUTPUT_OBJECT_KEY` is empty, the Lambda derives the name from the input key: `<job-name>.summary.json` under `OUTPUT_PREFIX`.
* If `OUTPUT_BUCKET` is empty, it falls back to the input bucket (not recommended).

3. **Create the Lambda**
    * Runtime: Python 3.x (boto3 is included)
    * Paste `lambda_function.py`
    * Set the environment variables above
    * Configure **Timeout** (e.g., 30–60s) and **Memory** (e.g., 256–512MB)

4. **S3 trigger**
    In the Lambda console (**Configuration → Triggers → Add trigger → S3**):
    * Event types: *All object create events*
    * (Recommended) Filter: `Suffix = .json`

5. **Transcribe job output**
   * Run **Amazon Transcribe** on your audio.
   * Configure the job to write its **Output** to the input bucket path `audio-transcript/`. 
   * The Lambda listens for that JSON.


## How It Works

* The Lambda determines the input from the S3 event (`bucket` + `key`). If invoked manually, it falls back to the defaults from environment variables.
* It reads the Transcribe JSON and extracts the transcript text from `results.transcripts[0].transcript`.
* It sends a **Messages**-formatted request to Bedrock (**Claude 3 Haiku**) with the transcript text and the prompt: *“סכם את השיחה בשלוש נקודות בעברית תקנית.”*
* It builds a compact JSON result and writes it to the output bucket using a dynamic name derived from the input key.


## Output (JSON)

Example file content:

```json
{
  "job": "audio-transcript/my-audio.json",
  "model": "anthropic.claude-3-haiku-20240307-v1:0",
  "prompt": "סכם את השיחה בשלוש נקודות בעברית תקנית.",
  "summary": "מכאן ניתן לסכם את השיחה בשלוש נקודות עיקריות:\n\n1. .....\n\n2. .....\n\n3. ....."
}
```

* Content-Type: `application/json; charset=utf-8`
* File naming: `<job-name>.summary.json` under `transcript-summaries/` (e.g., `my-audio.json` → `transcript-summaries/my-audio.summary.json`).


## Using the Pipeline

### A) Normal flow (S3 trigger)

1. Run an **Amazon Transcribe** job on your audio and set its output to the input bucket/prefix.
2. When the JSON lands in S3 (the default input bucket), the Lambda runs automatically.
3. Fetch the summary JSON from `s3://output-audio-transcripts-bucket/transcript-summaries/`.

### B) Manual test (Invoke with custom event)

Invoke the Lambda with a test event like:

```json
{
  "input_bucket": "my-audio-transaction-bucket",
  "input_object_key": "audio-transcript/my-audio.json",
  "output_bucket": "output-audio-transcripts-bucket",
  "output_object_key": "transcript-summaries/override-name.summary.json"
}
```
> If no event is provided, the Lambda uses the environment defaults.


## My Reflection

* **Approach:** *TBD*
* **Challenges:** *TBD*
* **How I solved them:** *TBD*


## License

This project is licensed under the MIT License.  
See the [LICENSE](./LICENSE) file for details.
