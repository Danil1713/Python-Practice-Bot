import random

balance = 1000
games = 0
wins = 0
losses = 0
max_balance = balance

print("=" * 35)
print("🎰       PYTHON MINI CASINO")
print("=" * 35)

while balance > 0:
    print()
    print(f"💰 Твой баланс: {balance} монет")
    print()

    bet = input("Введи ставку или 'exit' для выхода: ")

    if bet.lower() == "exit":
        break

    if not bet.isdigit():
        print("❌ Нужно ввести число.")
        continue

    bet = int(bet)

    if bet <= 0:
        print("❌ Ставка должна быть больше нуля.")
        continue

    if bet > balance:
        print("❌ У тебя недостаточно монет.")
        continue

    print()
    print("🎲 Барабан вращается...")

    result = random.randint(1, 100)

    games += 1

    if result <= 5:
        win = bet * 5
        balance += win
        wins += 1

        print("💎 ДЖЕКПОТ!")
        print(f"Ты выиграл +{win} монет!")

    elif result <= 45:
        balance += bet
        wins += 1

        print("🔥 ПОБЕДА!")
        print(f"Ты выиграл +{bet} монет!")

    else:
        balance -= bet
        losses += 1

        print("💀 Проигрыш.")
        print(f"Ты потерял {bet} монет.")

    if balance > max_balance:
        max_balance = balance

    print()
    print(f"💰 Новый баланс: {balance}")

    if balance == 0:
        print()
        print("💸 У тебя закончились монеты.")
        break

    print()
    answer = input("Играть ещё? (yes/no): ")

    if answer.lower() != "yes":
        break


print()
print("=" * 35)
print("📊       СТАТИСТИКА ИГРЫ")
print("=" * 35)

print(f"Всего игр:           {games}")
print(f"Побед:               {wins}")
print(f"Поражений:           {losses}")
print(f"Максимальный баланс: {max_balance}")
print(f"Итоговый баланс:     {balance}")

print()
print("Спасибо за игру 👋")