from discord import Interaction, ButtonStyle, Color
from discord.ui import View, Button, button

from core.functions import create_basic_embed

class OptionView(View):  
    def __init__(self, *, timeout = 180, key: str, value: str, correct_word: str, correct_meanings: list, wrong_datas: list, option_dict: dict):
        super().__init__(timeout=timeout)

        self.key = key # a, b, c...
        self.value = value # word, like 'apple', 'banana'
        self.correct_word = correct_word # apple
        self.correct_meanings = correct_meanings
        self.wrong_datas = wrong_datas

        self.option_dict = option_dict

        self.button_callback.label = value

    @button(label='Unknown', style=ButtonStyle.primary)  
    async def button_callback(self, inter: Interaction, button: Button):
        await inter.response.defer(thinking=True)
        option = button.label

        if option == self.correct_word:
            # see others meanings
            button = Button(label='See others meanings', style=ButtonStyle.primary)
            async def other_info_button_callback(inter: Interaction):
                star_func = lambda x: '**' if x['word'] == self.correct_word else ''
                strings = []

                for item in self.wrong_datas:
                    word = item['word']
                    meanings = item['meanings']

                    _index = list(self.option_dict.values()).index(word)
                    key = list(self.option_dict.keys())[_index]
                    strings.append(star_func(item) + f"({key}) {word}: {meanings}" + star_func(item))

                await inter.response.send_message('\n'.join(strings))
            button.callback = other_info_button_callback # type: ignore

            _view = View()
            _view.add_item(button)
            await inter.followup.send(f'Correct!\n\nClick the button below to see others meanings', view=_view)
        else:
            eb = create_basic_embed(
                f'You are WRONG!!! Try again', 
                f'## ({self.key}) {option}\n### Meanings:\n`{'; '.join(self.correct_meanings)}`', 
                color=Color.red()
            )
            await inter.followup.send(embed=eb)
            