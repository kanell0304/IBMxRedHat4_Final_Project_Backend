import json
import httpx
from typing import Dict
from app.core.settings import settings
from app.prompts.interview_prompts import build_prompt, SYSTEM_MESSAGE
from app.service.llm.base import BaseLLMService



class WatsonxService(BaseLLMService):

    def __init__(self):
        self.api_key=settings.watsonx_api_key
        self.project_id=settings.watson_project_id
        self.url=settings.watsonx_url
        self.model=settings.watsonx_model


    async def get_watsonx_access_token(self):
        async with httpx.AsyncClient() as client:
            response=await client.post(
                "https://iam.cloud.ibm.com/identify/token",
                headers={"Content-Type":"application/x-www-form-urlencoded"},
                data={
                    "grant_type":"urn:ibm:params:oauth:grant-type:apikey",
                    "apikey":self.api_key
                }
            )

            print(f"Status Code : {response.status_code}")
            print(f"Response : {response.text}")


            response.raise_for_status()
            token_data=response.json()


            if "access_token" not in token_data:
                raise ValueError(f"access_token not found : {token_data}")
            return token_data["access_token"]


    async def generate_report(self, transcript:str, bert_analysis:Dict):
        try:

            access_token=await self.get_watsonx_access_token()

            
            prompt=build_prompt(transcript, bert_analysis)
            full_prompt=f"{SYSTEM_MESSAGE}\n\n{prompt}"

            payload={
                "model_id":self.model,
                "input":full_prompt,
                "parameters":{
                    "decoding_method":"greedy",
                    "max_new_tokens":2000,
                    "temperature":0.3,
                    "stop_sequences":[]
                },
                "project_id":self.project_id
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response=await client.post(
                    f"{self.url}/ml/v1/text/generation?version=2023-05-29",
                    headers={
                        "Authorization":f"Bearer {access_token}",
                        "Content-Type":"application/json",
                        "Accept":"application/json"
                    },
                    json=payload
                )
                response.raise_for_status()

                data=response.json()

                # Watsonx 응답 구조
                generated_text=data.get("result", [{}])[0].get("generated_text", "")

                # JSON 추출
                if "```json" in generated_text:
                    generated_text=generated_text.split("```json")[1].split("```")[0]
                elif "```" in generated_text:
                    generated_text=generated_text.split("```")[1].split("```")[0]


                result=json.loads(generated_text.strip())
                return result
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Watsonx 응답 JSON 파싱 실패 : {e}")
