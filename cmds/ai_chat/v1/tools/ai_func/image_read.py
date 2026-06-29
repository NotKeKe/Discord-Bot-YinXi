from ...utils.client import AsyncClient


async def image_read(prompt: str, image_url: str) -> str:
    try:
        messages = [
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': prompt
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': image_url
                        }
                    }
                ]
            }
        ]

        client = AsyncClient.zhipu
        response = await client.chat.completions.create(
            model='glm-4v-flash',
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )

        return str(response.choices[0].message.content).strip()
    except Exception as e1: 
        return '圖片無法判讀' + str(e1)