greet_user = """\
Приветствую тебя, новообращённый {full_name}!
Если ты любишь Аск, но не любишь его косяки — присоединяйся к нашей секте.
Подробности у меня в профиле."""

rescuing_answer = "42"

login_ok = """\
Замечательно, доступ к аккаунту настроен.
Я записал зашифрованный пароль тебе в хештеги, чтобы не забыть. Извини за этот беспорядок~"""

login_failed = """\
Что-то пошло не так :(
Проверь пароль и попробуй ещё раз, солнышко^^"""

user_settings_map = {
    "да": True,
    "нет": False,
    #
    "стоп_машина": "stop",
    "яумамытестировщик": "test",
    #
    "спасать_старые_вопросы": "rescue",
    "удалять_вопросы_старше_N_дней": "delete_after",
    #
    "фильтр": "filters_str",
    "фильтр_рв": "filters_re",
    "читать_шаутауты": "read_shoutouts",
    "удалять_шаутауты": "delete_shoutouts",
    #
    "фильтр_блок_авторов": "filter_block_authors",
    "фильтр_только_анон": "filter_anon_only",
    #
    "режим_чистки": "filter_schedule",
    "непрерывно": "CONTINUOUS",
    "ежедневно": "DAILY",
    "по_запросу": "ON_DEMAND",
}
