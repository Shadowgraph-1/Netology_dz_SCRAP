import requests
from bs4 import BeautifulSoup
import time
import pprint

# Определяем список ключевых слов
KEYWORDS = ['дизайн', 'фото', 'web', 'python']

# Базовый URL для парсинга
BASE_URL = 'https://habr.com'

# Список URL для парсинга
URLS = [
    f'{BASE_URL}/ru/articles/',
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                  ' Chrome/85.0.4183.121 Safari/537.36',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
}

def fetch_page(url):
    """
    Функция для получения страницы с указанным URL.
    """
    try:
        response = requests.get(url=url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.text
    
    # Небольшая отладка
    # Обработчик ошибок связанных с запросами к сайту и т.д.
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP ошибка при запросе {url}: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Ошибка соединения при запросе {url}: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Тайм-аут при запросе {url}: {timeout_err}")
    except Exception as err:
        print(f"Неизвестная ошибка при запросе {url}: {err}")
    return None

def parse_articles(html):
    """
    Функция для парсинга списка статей со страницы.
    """
    soup = BeautifulSoup(html, 'html.parser')
    articles = soup.find_all('article')
    return articles

def extract_article_info(article):
    """
    Извлекает информацию о статье: заголовок, дату и ссылку.
    """
    title_tag = article.find('a', class_='tm-title__link', attrs={'data-article-link': 'true'})
    date_tag = article.find('time')
    
    if title_tag and date_tag:
        # Извлекаем дату из атрибута 'title'
        date_text = date_tag.get('title', '').strip()
        if not date_text:
            date_text = date_tag.get_text(strip=True)

        # Извлекаем заголовок
        original_title = title_tag.get_text(strip=True)

        # Извлекаем ссылку на статью
        href = title_tag.get('href', '')
        if href.startswith('/'):
            link = BASE_URL + href
        else:
            link = href

        return {
            'title': original_title,
            'title_lower': original_title.lower(),
            'date': date_text,
            'link': link
        }
    return None

def fetch_full_text(url):
    """
    Получает полный текст статьи по её URL.
    """
    html = fetch_page(url)
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Попробуем разные варианты контейнеров для контента статьи
        possible_containers = [
            'div.post__text',          # Стандартные статьи
            'div.article-formatted-body',  # Возможно для компаний
            'div.tm-article-presenter__body', # Новая структура
            'div.article__text'        # Альтернативный вариант
        ]
        
        content = None
        for selector in possible_containers:
            content = soup.select_one(selector)
            if content:
                break
        
        if content:
            # Убираем все теги и получаем текст
            return content.get_text(separator='\n', strip=True)
        else:
            print(f"Не удалось найти контейнер с контентом для {url}")
    else:
        print(f"Не удалось загрузить страницу {url}")
    return ""

def print_articles(articles_dict):
    """
    Функция для печати списка статей с нумерацией и категориями.
    """
    print("\nСписок статей:")
    print("--------------")
    for number, article in articles_dict.items():
        category = "📌 Ключевое" if article['category'] == 'matching' else "📄 Другое"
        print(f"{number}. [{category}] {article['date']} - {article['title']}")

def main():
    # Получаем HTML всех страниц
    all_articles_html = []
    for url in URLS:
        page_content = fetch_page(url)
        if page_content:
            articles = parse_articles(page_content)
            all_articles_html.extend(articles)
            print(f"Найдено {len(articles)} статей на странице {url}")
        else:
            print(f"Не удалось получить контент с {url}")

    if not all_articles_html:
        print("Не удалось найти статьи на всех страницах.")
        return

    matching_articles = []  # Статьи с ключевыми словами в заголовке или тексте
    other_articles = []     # Остальные статьи

    print("Обрабатываем статьи, пожалуйста, подождите...")

    # Чтобы избежать дублирования статей, будем отслеживать ссылки
    processed_links = set()

    for article in all_articles_html:
        info = extract_article_info(article)
        if info and info['link'] not in processed_links:
            processed_links.add(info['link'])
            # Проверяем ключевые слова в заголовке
            in_title = any(keyword in info['title_lower'] for keyword in KEYWORDS)

            # Инициализируем переменную для проверки в тексте
            in_text = False

            if not in_title:
                # Если ключевых слов нет в заголовке, проверяем в тексте статьи
                full_text = fetch_full_text(info['link'])
                if any(keyword in full_text.lower() for keyword in KEYWORDS):
                    in_text = True
                # Добавляем небольшую задержку, чтобы не перегружать сервер
                time.sleep(1)

            if in_title or in_text:
                matching_articles.append(info)
            else:
                other_articles.append(info)

    # Создаем общий словарь статей с уникальной нумерацией
    all_articles = {}
    current_number = 1

    for article in matching_articles:
        all_articles[current_number] = {
            'title': article['title'],
            'date': article['date'],
            'link': article['link'],
            'category': 'matching'
        }
        current_number += 1

    for article in other_articles:
        all_articles[current_number] = {
            'title': article['title'],
            'date': article['date'],
            'link': article['link'],
            'category': 'other'
        }
        current_number += 1

    if all_articles:
        print_articles(all_articles)
    else:
        print("Нет доступных статей для отображения.")
        return

    # Предлагаем пользователю выбрать статью для просмотра
    while True:
        try:
            choice = input("\nВведите номер статьи для просмотра (или 'exit' для выхода): ").strip()
            if choice.lower() == 'exit':
                print("Выход из программы.")
                break
            choice = int(choice)
            if choice in all_articles:
                selected_article = all_articles[choice]
                # P.S:
                # ТЕКСТ МОЖЕТ ВЫВОДИТЬСЯ С ОШИБКАМИ(Неправильное отображение символов, обрывы в тексте и т.д)
                print(f"\nЗагружаем статью: {selected_article['title']}\n{'=' * (len(selected_article['title']) + 17)}")
                full_text = fetch_full_text(selected_article['link'])
                if full_text:
                    print(full_text)
                else:
                    print("Не удалось загрузить полный текст статьи.")
            else:
                print(f"Пожалуйста, введите число от 1 до {len(all_articles)}.")
        except ValueError:
            print("Пожалуйста, введите корректный номер или 'exit' для выхода.")

if __name__ == "__main__":
    main()
