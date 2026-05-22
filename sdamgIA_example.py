#!/usr/bin/env python3
"""
Скрипт для скачивания заданий по физике с сайта sdamgia.ru
Скачивает по 10 заданий по каждой теме/категории
"""

import json
import os
import time
from sdamgia import SdamGIA

def download_physics_problems():
    # Инициализация API
    sdamgia = SdamGIA()
    subject = 'phys'
    
    # Создаем директорию для сохранения
    output_dir = 'physics_problems'
    os.makedirs(output_dir, exist_ok=True)
    
    print("Получение каталога заданий по физике...")
    catalog = sdamgia.get_catalog(subject)
    
    if not catalog:
        print("Не удалось получить каталог")
        return
    
    print(f"Получено {len(catalog)} тем")
    
    # Словарь для хранения всех задач
    all_problems = {}
    
    for topic in catalog:
        topic_id = topic['topic_id']
        topic_name = topic['topic_name']
        categories = topic['categories']
        
        print(f"\nТема: {topic_name} (ID: {topic_id})")
        print(f"  Категорий: {len(categories)}")
        
        topic_problems = []
        
        for category in categories:
            category_id = category['category_id']
            category_name = category['category_name']
            
            print(f"    Категория: {category_name} (ID: {category_id})")
            
            try:
                # Получаем задачи из категории
                problems = sdamgia.get_category_by_id(subject, category_id)
                
                if problems:
                    # Берем первые 10 задач
                    problems_to_download = problems[:4]
                    print(f"      Найдено задач: {len(problems)}, скачиваем: {len(problems_to_download)}")
                    
                    category_problems = []
                    
                    for problem_id in problems_to_download:
                        try:
                            # Получаем полную информацию о задаче
                            problem_data = sdamgia.get_problem_by_id(subject, problem_id)
                            
                            if problem_data:
                                category_problems.append({
                                    'id': problem_id,
                                    'condition': problem_data.get('condition', {}),
                                    'solution': problem_data.get('solution', {}),
                                    'answer': problem_data.get('answer', ''),
                                    'url': problem_data.get('url', '')
                                })
                                print(f"        Скачана задача {problem_id}")
                            
                            # Небольшая задержка, чтобы не перегружать сервер
                            time.sleep(0.04)
                            
                        except Exception as e:
                            print(f"        Ошибка при скачивании задачи {problem_id}: {e}")
                    
                    topic_problems.append({
                        'category_id': category_id,
                        'category_name': category_name,
                        'problems': category_problems
                    })
                    
                else:
                    print(f"      Задач не найдено")
                
                # Задержка между категориями
                time.sleep(0.2)
                
            except Exception as e:
                print(f"      Ошибка при получении категории {category_id}: {e}")
        
        all_problems[topic_name] = {
            'topic_id': topic_id,
            'categories': topic_problems
        }
        
        # Сохраняем промежуточный результат
        with open(os.path.join(output_dir, f'topic_{topic_id}.json'), 'w', encoding='utf-8') as f:
            json.dump({
                'topic_name': topic_name,
                'topic_id': topic_id,
                'categories': topic_problems
            }, f, ensure_ascii=False, indent=2)
    
    # Сохраняем все задачи в один файл
    with open(os.path.join(output_dir, 'all_physics_problems.json'), 'w', encoding='utf-8') as f:
        json.dump(all_problems, f, ensure_ascii=False, indent=2)
    
    print(f"\nГотово! Все задачи сохранены в директории: {output_dir}")
    print(f"Всего тем: {len(all_problems)}")

if __name__ == '__main__':
    download_physics_problems()
