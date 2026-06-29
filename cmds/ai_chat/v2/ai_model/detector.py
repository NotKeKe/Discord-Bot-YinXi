import re

from ..data_keeper.data import DATA_STORE
from ..types.chater import Model

class ModelDetector:
    @staticmethod
    def detect_to_model(model: str) -> Model:
        """將使用者傳的 `provider:model` 轉為 Model type

        Args:
            model (str): _description_

        Raises:
            ValueError: 如果完全找不到 model，就會 raise 此 error

        Returns:
            Model: _description_
        """              
        
        match = re.match(r"(.*?)\s*:\s*(.*)", model)

        if match:
            provider = match.group(1)
            model = match.group(2)

            if provider and model:
                return Model(provider=provider, model=model)
        
        # 搜尋最相近的模型
        for p in DATA_STORE.available_providers.keys():
            if model in DATA_STORE.available_providers[p]['models']:
                return Model(provider=p, model=model)


        raise ValueError(f"Invalid model: {model}")
