import asyncio
import json
import logging
import time
from typing import Dict, List, Union
from uuid import uuid4

import aiohttp
from api_v1.settings import settings
from fastapi import APIRouter, Depends, Response, Security, status
from gpt4all import GPT4All
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

### This should follow https://github.com/openai/openai-openapi/blob/master/openapi.yaml


class CompletionRequest(BaseModel):
    model: str = Field(..., description='The model to generate a completion from.')
    prompt: Union[List[str], str] = Field(..., description='The prompt to begin completing from.')
    max_tokens: int = Field(7, description='Max tokens to generate')
    temperature: float = Field(0, description='Model temperature')
    top_p: float = Field(1.0, description='top_p')
    top_k: int = Field(50, description='top_k')
    n: int = Field(1, description='How many completions to generate for each prompt')
    stream: bool = Field(False, description='Stream responses')
    output_scores: bool = Field(False, description='Whether to output scores')
    repeat_penalty: float = Field(1.0, description='Repeat penalty')
    do_sample: bool = Field(True, description='Whether to sample')
    num_beams: int = Field(1, description='Number of beams')


class CompletionChoice(BaseModel):
    text: str
    index: int
    logprobs: float
    finish_reason: str


class CompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class CompletionResponse(BaseModel):
    id: str
    object: str = 'text_completion'
    created: int
    model: str
    choices: List[CompletionChoice]
    usage: CompletionUsage


router = APIRouter(prefix="/completions", tags=["Completion Endpoints"])


async def infer(payload, header):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                settings.hf_inference_server_host, headers=header, data=json.dumps(payload)
            ) as response:
                resp = await response.json()
            return resp

        except aiohttp.ClientError as e:
            # Handle client-side errors (e.g., connection error, invalid URL)
            logger.error(f"Client error: {e}")
        except aiohttp.ServerError as e:
            # Handle server-side errors (e.g., internal server error)
            logger.error(f"Server error: {e}")
        except json.JSONDecodeError as e:
            # Handle JSON decoding errors
            logger.error(f"JSON decoding error: {e}")
        except Exception as e:
            # Handle other unexpected exceptions
            logger.error(f"Unexpected error: {e}")


@router.post("/", response_model=CompletionResponse)
async def completions(request: CompletionRequest):
    '''
    Completes a GPT4All model response.
    '''

    # global model
    if request.stream:
        raise NotImplementedError("Streaming is not yet implemented")

    if settings.inference_mode == "gpu":
        params = request.dict(exclude={'model', 'prompt', 'max_tokens', 'n'})
        params["max_new_tokens"] = request.max_tokens
        params["num_return_sequences"] = request.n

        header = {"Content-Type": "application/json"}
        payload = {"parameters": params}
        if isinstance(request.prompt, list):
            tasks = []
            for prompt in request.prompt:
                payload["inputs"] = prompt
                task = infer(payload, header)
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            choices = []
            for response in results:
                scores = response["scores"] if "scores" in response else -1.0
                choices.append(
                    dict(
                        CompletionChoice(
                            text=response["generated_text"], index=0, logprobs=scores, finish_reason='stop'
                        )
                    )
                )

            return CompletionResponse(
                id=str(uuid4()),
                created=time.time(),
                model=request.model,
                choices=choices,
                usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            )

        else:
            payload["inputs"] = request.prompt

            resp = await infer(payload, header)

            output = resp["generated_text"]
            # this returns all logprobs
            scores = resp["scores"] if "scores" in resp else -1.0

            return CompletionResponse(
                id=str(uuid4()),
                created=time.time(),
                model=request.model,
                choices=[dict(CompletionChoice(text=output, index=0, logprobs=scores, finish_reason='stop'))],
                usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            )

    else:
        model = GPT4All(model_name=settings.model, model_path=settings.gpt4all_path)

        if isinstance(request.prompt, list):
            choices = []
            for prompt in request.prompt:
                output = model.generate(
                    prompt=prompt,
                    n_predict=request.max_tokens,
                    top_k=20,
                    top_p=request.top_p,
                    temp=request.temperature,
                    n_batch=1024,
                    repeat_penalty=1.2,
                    repeat_last_n=10,
                    context_erase=0,
                )
                choices.append(dict(CompletionChoice(text=output, index=0, logprobs=-1, finish_reason='stop')))

            return CompletionResponse(
                id=str(uuid4()),
                created=time.time(),
                model=request.model,
                choices=choices,
                usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            )

        else:
            output = model.generate(
                prompt=request.prompt,
                n_predict=request.max_tokens,
                top_k=20,
                top_p=request.top_p,
                temp=request.temperature,
                n_batch=1024,
                repeat_penalty=1.2,
                repeat_last_n=10,
                context_erase=0,
            )

            return CompletionResponse(
                id=str(uuid4()),
                created=time.time(),
                model=request.model,
                choices=[dict(CompletionChoice(text=output, index=0, logprobs=-1, finish_reason='stop'))],
                usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            )
