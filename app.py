from datetime import date
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Attr
from fastapi import FastAPI, HTTPException

app = FastAPI()

# TODO: build image and post to ECR
# TODO: host on ec2 with dynamodb access
dynamo = boto3.resource(
    "dynamodb",
    region_name="us-east-1",
)
daily_metrics = dynamo.Table("DailyMetrics")


@app.get("/dailymetrics/{date}")
def get_metrics(date: date):
    try:
        return daily_metrics.get_item(Key={"date": str(date)})["Item"]
    except KeyError:
        raise HTTPException(status_code=404, detail="Item not found")
    except Exception:
        return HTTPException(500, "ServerError")


@app.post("/dailymetrics/{date}")
def add_metrics(
    date: date,
    mood: float | None = None,
    sleep: float | None = None,
    productivity: float | None = None,
    stress: float | None = None,
):
    try:
        for x in (mood, sleep, productivity, stress):
            float(x)
    except ValueError:
        raise HTTPException(400, "Metrics should be real numbers")
    try:
        resp = daily_metrics.put_item(
            Item={
                "date": str(date),
                "mood": Decimal(str(mood)),
                "sleep": Decimal(str(sleep)),
                "productivity": Decimal(str(productivity)),
                "stress": Decimal(str(stress)),
            },
            ConditionExpression=Attr("date").not_exists(),
        )
        print(resp)
    except dynamo.meta.client.exceptions.ConditionalCheckFailedException:
        raise HTTPException(400, "Metric already exists")


@app.delete("/dailymetrics/{date}")
def delete_metrics(date: date):
    try:
        resp = daily_metrics.delete_item(
            Key={"date": str(date)}, ConditionExpression=Attr("date").exists()
        )
    except dynamo.meta.client.exceptions.ConditionalCheckFailedException as e:
        raise HTTPException(404, "Item does not exists") from e
    except Exception as e:
        raise HTTPException(500, "ServerError") from e


@app.patch("/dailymetrics/{date}")
def update_metrics(
    date: date,
    mood: float | None = None,
    sleep: float | None = None,
    productivity: float | None = None,
    stress: float | None = None,
):
    payload = {
        k: v
        for k, v in {
            "mood": mood,
            "sleep": sleep,
            "productivity": productivity,
            "stress": stress,
        }.items()
        if v
    }

    try:
        return daily_metrics.update_item(
            Key={
                "date": str(date),
            },
            ExpressionAttributeValues={
                **{f":{k}": Decimal(str(v)) for k, v in payload.items()}
            },
            UpdateExpression="SET " + ", ".join([f"{k}=:{k}" for k in payload]),
            ReturnValues="ALL_NEW",
        )["Attributes"]
    except Exception as e:
        raise HTTPException(500, "ServerError") from e
