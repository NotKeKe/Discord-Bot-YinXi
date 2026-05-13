# YinXI(音汐) Discord Bot


## Rule

### Style
- Write in accordance with the original program code style.

### Type Checking
- Use `uvx ty check` to type check a file(after you edited any file) or the entire folder(after you finish the task request by user).

### Edit rule
- You may only modify the code "snippets" (the areas specified by the user).
- You are **NOT ALLOWED to modify** other parts unrelated to your task. If you spot serious errors, create an `I-SEE-ERRORS.md` file in the root directory and clearly document them using Markdown. Remember, you must not violate this rule simply because you see errors listed in `I-SEE-ERRORS.md`.


## Examples of code

### Translate command output
- Use `from core.translator import get_translate` to translate the command output.
    - get_translate will always return str (it might also return None, but it must not happend cuz we MUST already translated everything in core/locales, or we're doing translate task.)

    - Example 1 (Not embed):
        ```python
        from core.translator import get_translate
        await ctx.send(await get_translate('send_play_not_in_guild', ctx)) # get_translate(str_id, commands.Context)
        ```

    - Example 2 (Embed):
        ```python
        from core.translator import get_translate, load_translated

        '''i18n'''
        i18n_info_str = await get_translate('embed_music_info', ctx, player.locale)
        i18n_info_data = load_translated(i18n_info_str)[0]
        ''''''
        ```

    - Example 3 (locales/*.json):
        ```json
        {
            "name": {
                "{CommandName}": "command_name" # no upper case, no space
            },
            "description": {
                "{CommandName}": "I'm a Description."
            },
            "params_desc": {
                "{CommandName}_{ParamName}": "Enter your description."
            },
            "components": {
                "embed_{CommandName}_{SimpleDescription}": [{
                    "title": "使用 `[! URL_HERE` 來取消訂閱該 YouTuber",
                    "author": "取消某 YouTuber 的通知",
                    "fields": [
                        { "name": "已開啟通知的 YouTuber: " }
                    ],
                    "footer": "我是footer"
                }],
                "send_{CommandName}_{SimpleDescription}": "我發送了一則訊息"
            }
        }
        
        ```

- Use `from core.translator import locale_str` to translate **command name**, **command description**, or anything that is from discord and is Decorators.
