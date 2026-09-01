from pathlib import Path
import shutil


CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
    "Videos": [".mp4", ".mov", ".avi", ".mkv"],
    "Documents": [".pdf", ".txt", ".docx", ".xlsx"],
    "Archives": [".zip", ".rar", ".7z"],
}


def get_category(extension):
    extension = extension.lower()

    for category, extensions in CATEGORIES.items():
        if extension in extensions:
            return category

    return "Other"


def sort_folder(folder_path):
    folder = Path(folder_path)

    if not folder.exists():
        print("❌ Такой папки не существует.")
        return

    if not folder.is_dir():
        print("❌ Нужно указать именно папку.")
        return

    moved_files = 0

    print()
    print("📁 Начинаю сортировку...")
    print()

    for file in folder.iterdir():

        if not file.is_file():
            continue

        category = get_category(file.suffix)

        destination_folder = folder / category
        destination_folder.mkdir(exist_ok=True)

        destination = destination_folder / file.name

        shutil.move(str(file), str(destination))

        moved_files += 1

        print(f"✅ {file.name} → {category}")

    print()
    print("=" * 40)
    print(f"🎉 Готово! Перемещено файлов: {moved_files}")
    print("=" * 40)


folder_path = input("📂 Введи путь к папке: ")

sort_folder(folder_path)