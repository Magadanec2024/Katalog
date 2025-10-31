import PyInstaller.__main__
import os
import shutil

def build_app():
    """Сборка исполняемого файла приложения"""
    
    # Удаляем старую сборку
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')
    
    # Параметры для PyInstaller
    args = [
        'main.py',
        '--name=ProductCalculator',
        '--windowed',  # Для GUI приложения
        '--onefile',   # В один файл
        '--add-data=data;data',  # Добавляем папку data
        '--hidden-import=pandas',
        '--hidden-import=openpyxl',
        '--hidden-import=reportlab',
        '--hidden-import=sqlite3',
        '--clean',
        '--noconfirm'
    ]
    
    # Запускаем PyInstaller
    PyInstaller.__main__.run(args)
    
    print("Сборка завершена! Исполняемый файл находится в папке dist/")

if __name__ == '__main__':
    build_app()