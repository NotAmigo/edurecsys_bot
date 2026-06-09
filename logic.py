import pandas as pd

MAX_RECOMMENDATION = 10
DATAFRAME_PATH = "dataframe.csv"

class PsychologyType:
    count = 0
    clusters = ()

    def __init__(self, clusters, name, count=0):
        self.count = count
        self.clusters = clusters
        self.name = name


class Test:
    # 5 - Психология
    # 3 - Маркетплейсы
    # 4 - Аналитик
    # 6 - Дизайн, верстка
    # 7 - Управление, менеджмент
    # 8 - Разработка и тестирование
    # 9 - Коммуникация
    # 0 - Финансы и бизнес
    # 1 - Нейросети
    # 2 - Маркетинг и PR
    REALISTIC = ()
    INTELLIGENT = (8, 1)
    SOCIAL = (2, 5, 9)
    CONVENTION = (4)
    ENTREPRENEURIAL = (0, 3, 7)
    ART = (6)

    def __init__(self):
        self.REALISTIC = PsychologyType([], "Реалистичный")
        self.INTELLIGENT = PsychologyType([1, 8], "Исследовательский")
        self.SOCIAL = PsychologyType([2, 5, 9], "Социальный")
        self.CONVENTION = PsychologyType([4], "Конвенциональный")
        self.ENTREPRENEURIAL = PsychologyType([0, 3, 7], "Предпринимательский")
        self.ART = PsychologyType([6], "Артистический")

    def helper(self, item: PsychologyType):
        return {"clusters": item.clusters, "count": item.count, "name": item.name}

    def get_count(self):
        return [self.helper(self.REALISTIC),
                self.helper(self.INTELLIGENT), self.helper(self.SOCIAL),
                self.helper(self.CONVENTION), self.helper(self.ENTREPRENEURIAL),
                self.helper(self.ART)]


def analyze_test(answers: dict):
    '''
    params: ответы пользователя в формате словаря(ex. {"1": "А", ...})
    returns: три психотипа(от более сильновыраженного к менее) в формате списка
    '''
    statictic = Test()
    if answers["1"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.INTELLIGENT.count += 1

    if answers["2"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.SOCIAL.count += 1

    if answers["3"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.CONVENTION.count += 1

    if answers["4"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.ENTREPRENEURIAL.count += 1

    if answers["5"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.ART.count += 1

    if answers["6"] == "A":
        statictic.INTELLIGENT.count += 1
    else:
        statictic.SOCIAL.count += 1

    if answers["7"] == "A":
        statictic.INTELLIGENT.count += 1
    else:
        statictic.CONVENTION.count += 1

    if answers["8"] == "A":
        statictic.INTELLIGENT.count += 1
    else:
        statictic.ENTREPRENEURIAL.count += 1

    if answers["9"] == "A":
        statictic.INTELLIGENT.count += 1
    else:
        statictic.ART.count += 1

    if answers["10"] == "A":
        statictic.SOCIAL.count += 1
    else:
        statictic.CONVENTION.count += 1

    if answers["11"] == "A":
        statictic.SOCIAL.count += 1
    else:
        statictic.ENTREPRENEURIAL.count += 1

    if answers["12"] == "A":
        statictic.SOCIAL.count += 1
    else:
        statictic.ART.count += 1

    if answers["13"] == "A":
        statictic.CONVENTION.count += 1
    else:
        statictic.ENTREPRENEURIAL.count += 1

    if answers["14"] == "A":
        statictic.CONVENTION.count += 1
    else:
        statictic.ART.count += 1

    if answers["15"] == "A":
        statictic.ENTREPRENEURIAL.count += 1
    else:
        statictic.ART.count += 1

    if answers["16"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.INTELLIGENT.count += 1

    if answers["17"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.SOCIAL.count += 1

    if answers["18"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.CONVENTION.count += 1

    if answers["19"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.ART.count += 1

    if answers["20"] == "A":
        statictic.INTELLIGENT.count += 1
    else:
        statictic.SOCIAL.count += 1

    if answers["21"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.ART.count += 1

    if answers["22"] == "A":
        statictic.INTELLIGENT.count += 1
    else:
        statictic.CONVENTION.count += 1

    if answers["23"] == "A":
        statictic.INTELLIGENT.count += 1
    else:
        statictic.ENTREPRENEURIAL.count += 1

    if answers["24"] == "A":
        statictic.INTELLIGENT.count += 1
    else:
        statictic.ART.count += 1

    if answers["25"] == "A":
        statictic.SOCIAL.count += 1
    else:
        statictic.CONVENTION.count += 1

    if answers["26"] == "A":
        statictic.SOCIAL.count += 1
    else:
        statictic.ENTREPRENEURIAL.count += 1

    if answers["27"] == "A":
        statictic.SOCIAL.count += 1
    else:
        statictic.ART.count += 1

    if answers["28"] == "A":
        statictic.CONVENTION.count += 1
    else:
        statictic.ENTREPRENEURIAL.count += 1

    if answers["29"] == "A":
        statictic.CONVENTION.count += 1
    else:
        statictic.ART.count += 1

    if answers["30"] == "A":
        statictic.ENTREPRENEURIAL.count += 1
    else:
        statictic.ART.count += 1

    if answers["31"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.INTELLIGENT.count += 1

    if answers["32"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.CONVENTION.count += 1

    if answers["33"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.ENTREPRENEURIAL.count += 1

    if answers["34"] == "A":
        statictic.REALISTIC.count += 1
    else:
        statictic.ART.count += 1

    if answers["35"] == "A":
        statictic.INTELLIGENT.count += 1
    else:
        statictic.ENTREPRENEURIAL.count += 1

    if answers["36"] == "A":
        statictic.INTELLIGENT.count += 1
    else:
        statictic.SOCIAL.count += 1

    if answers["37"] == "A":
        statictic.INTELLIGENT.count += 1
    else:
        statictic.ENTREPRENEURIAL.count += 1

    if answers["38"] == "A":
        statictic.SOCIAL.count += 1
    else:
        statictic.CONVENTION.count += 1

    if answers["39"] == "A":
        statictic.SOCIAL.count += 1
    else:
        statictic.ENTREPRENEURIAL.count += 1

    if answers["40"] == "A":
        statictic.CONVENTION.count += 1
    else:
        statictic.ENTREPRENEURIAL.count += 1

    if answers["41"] == "A":
        statictic.ART.count += 1
    else:
        statictic.SOCIAL.count += 1

    if answers["42"] == "A":
        statictic.CONVENTION.count += 1
    else:
        statictic.ART.count += 1

    top = sorted(statictic.get_count(), key=lambda x: x['count'], reverse=True)[:3]

    clusters = sum([x["clusters"] for x in top], [])

    count = MAX_RECOMMENDATION // len(clusters) + 1
    recommendation = pd.DataFrame()
    dataframe = pd.read_csv("clustered_courses.csv")

    pd.set_option('display.max_columns', None)

    pd.set_option('display.max_rows', None)

    pd.set_option('display.expand_frame_repr', False)

    pd.set_option('display.max_colwidth', 100)  # Укажите нужное значение

    for clust in clusters:
        target_dataframe = dataframe[dataframe['cluster'] == clust]
        target_dataframe = target_dataframe.sample(min(count, len(target_dataframe)))
        target_dataframe['price'] = target_dataframe['price_per_month'] # * target_dataframe['duration']
        target_dataframe = target_dataframe[['title', 'description', 'price', 'url']]
        recommendation = pd.concat([recommendation, target_dataframe])
    recommendation = recommendation.reset_index()
    recommendation.columns = ['id', 'title', 'description', 'price', 'url']
    return recommendation, [x["name"] for x in top]

