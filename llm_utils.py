import asyncio


async def run_prompt(client, prompt: str, model: str = "gpt-4o-mini", max_tokens: int = 2500) -> str:
    def _call_model():
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    return await asyncio.to_thread(_call_model)
