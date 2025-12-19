import random
from typing import List, Dict, Optional
# from dataclasses import dataclass


class Participant:
    def __init__(self, first_name: str, last_name: str, speaker_count: int=0, listener_count: int=0, observer_count: int=0):
        self.first_name = first_name
        self.last_name = last_name
        self.speaker_count = speaker_count
        self.listener_count = listener_count
        self.observer_count = observer_count


class WebinarRoleDistributor:
    def __init__(self, participants: List[Participant]):
        self.participants = participants.copy()
        self.rounds: List[Dict] = []
        self.current_round = 0
        self.next_speaker: Optional[Participant] = None
        self.max_rounds = len(participants)  # Каждый должен быть выступающим ровно 1 раз
        self.observers_per_round = 2 if len(participants) >= 15 else 1
        self.listeners_per_round = 2  # Всегда 2 слушателя

    def display_participants(self):
        for i, participant in self.participants:
            print(f"{i+1}. {participant.first_name} {participant.last_name}")

    def delete_participant(self, participant: Participant):
        if participant in self.participants:
            self.participants.remove(participant)
            print(f"Участник {participant.first_name} {participant.last_name} удален из списка")
        else:
            print(f"Участника {participant.first_name} {participant.last_name} нет в списке")

    def distribute_roles(self) -> bool:
        """Распределяет роли с учётом всех требований"""
        if len(self.participants) < 5:
            print("\nОшибка: минимальное количество участников - 5")
            return False

        self.rounds = []
        self.current_round = 0

        # Первый раунд - случайный выступающий
        first_speaker = self._select_random_speaker()
        if not first_speaker:
            return False

        self.next_speaker = self._select_preparing_participant(
            exclude=[first_speaker])

        while self._distribute_next_round():
            pass

        # Проверяем, все ли побывали слушателями и наблюдателями
        self._balance_roles()
        return True

    def _distribute_next_round(self) -> bool:
        if self.current_round >= self.max_rounds:
            return False

        speaker = self.next_speaker if self.next_speaker else self._select_random_speaker()
        if not speaker:
            return False

        preparing = self._select_preparing_participant(exclude=[speaker])
        if not preparing and len(self.rounds) < self.max_rounds - 1:
            return False

        # Выбираем слушателей (всегда 2)
        listeners = self._select_listeners(
            exclude=[speaker, preparing] if preparing else [speaker],
            count=self.listeners_per_round,
            force_unserved=True
        )

        # Выбираем наблюдателей (1 или 2 в зависимости от количества участников)
        observers = self._select_observers(
            exclude=[speaker, preparing] + listeners if preparing else [speaker] + listeners,
            count=self.observers_per_round,
            force_unserved=True
        )

        # Фиксируем роли
        speaker.speaker_count += 1
        for listener in listeners:
            listener.listener_count += 1
        for observer in observers:
            observer.observer_count += 1

        self.rounds.append({
            "round": self.current_round + 1,
            "speaker": speaker,
            "preparing": preparing,
            "listeners": listeners,
            "observers": observers
        })

        self.next_speaker = preparing
        self.current_round += 1
        return True

    def _balance_roles(self):
        """Балансирует роли, чтобы все побывали слушателями и наблюдателями"""
        for participant in self.participants:
            # Если участник ещё не был слушателем
            while participant.listener_count == 0:
                self._assign_as_listener(participant)

            # Если участник ещё не был наблюдателем
            while participant.observer_count == 0:
                self._assign_as_observer(participant)

    def _assign_as_listener(self, participant: Participant):
        """Назначает участника слушателем в подходящем раунде"""
        for round_data in self.rounds:
            if (participant not in round_data["listeners"] and
                participant != round_data["speaker"] and
                participant != round_data["preparing"] and
                participant not in round_data["observers"]):

                # Заменяем одного из слушателей с минимальным количеством раз
                if len(round_data["listeners"]) > 0:
                    replaced = min(round_data["listeners"], key=lambda x: x.listener_count)
                    if replaced.listener_count > 1:  # Меняем только если у заменяемого >1 раз
                        round_data["listeners"].remove(replaced)
                        replaced.listener_count -= 1
                        round_data["listeners"].append(participant)
                        participant.listener_count += 1
                        return

    def _assign_as_observer(self, participant: Participant):
        """Назначает участника наблюдателем в подходящем раунде"""
        for round_data in self.rounds:
            if (len(round_data["observers"]) > 0 and
                participant != round_data["speaker"] and
                participant != round_data["preparing"] and
                participant not in round_data["listeners"]):

                # Меняем наблюдателя с максимальным количеством раз
                replaced = max(round_data["observers"], key=lambda x: x.observer_count)
                if replaced.observer_count > 1 or participant.observer_count == 0:
                    round_data["observers"].remove(replaced)
                    replaced.observer_count -= 1
                    round_data["observers"].append(participant)
                    participant.observer_count += 1
                    return

    def _select_random_speaker(self) -> Optional[Participant]:
        candidates = [p for p in self.participants if p.speaker_count == 0]
        return random.choice(candidates) if candidates else None

    def _select_preparing_participant(self, exclude: List[Participant] = None) -> Optional[Participant]:
        exclude = exclude or []
        candidates = [p for p in self.participants
                      if p not in exclude and p.speaker_count == 0]
        return random.choice(candidates) if candidates else None

    def _select_listeners(self, exclude: List[Participant] = None, count: int = 2,
                          force_unserved: bool = False) -> List[Participant]:
        exclude = exclude or []
        if force_unserved:
            # Сначала выбираем тех, кто ещё не был слушателем
            candidates = [p for p in self.participants
                          if p not in exclude and p.listener_count == 0]
            if len(candidates) >= count:
                return random.sample(candidates, count)
        
        # Если не хватает "необслуженных", берём любых подходящих
        candidates = [p for p in self.participants
                      if p not in exclude]
        # Сортируем по количеству раз в роли слушателя (меньше раз - выше приоритет)
        candidates.sort(key=lambda x: x.listener_count)
        return candidates[:count]

    def _select_observers(self, exclude: List[Participant] = None, count: int = 1,
                          force_unserved: bool = False) -> List[Participant]:
        exclude = exclude or []
        if force_unserved:
            # Сначала выбираем тех, кто ещё не был наблюдателем
            candidates = [p for p in self.participants
                          if p not in exclude and p.observer_count == 0]
            if len(candidates) >= count:
                return random.sample(candidates, count)
        
        # Если все уже были наблюдателями, выбираем тех, у кого меньше всего раз
        candidates = [p for p in self.participants
                      if p not in exclude]
        # Сортируем по количеству раз в роли наблюдателя (меньше раз - выше приоритет)
        candidates.sort(key=lambda x: x.observer_count)
        return candidates[:count]

    def print_rounds(self):
        """Выводит распределение ролей и статистику"""
        
        print("\n=== Распределение ролей ===")
        for round_data in self.rounds:
            print(f"\nРаунд {round_data['round']}")
            print(f"Выступающий: {round_data['speaker'].full_name}")
            print(f"Готовящийся: {round_data['preparing'].full_name if round_data['preparing'] else 'нет'}")
            listeners = ", ".join([l.full_name for l in round_data['listeners']])
            print(f"Слушатели: {listeners}")
            observers = ", ".join([o.full_name for o in round_data['observers']])
            print(f"Наблюдатели: {observers}")

        # Статистика по участникам
        print("\n=== Статистика по участникам ===")
        for participant in sorted(self.participants, key=lambda x: x.last_name):
            print(f"{participant.full_name}: выступает - {participant.speaker_count} {get_suffix(participant.speaker_count)}, "
                  f"слушает - {participant.listener_count} {get_suffix(participant.listener_count)}, "
                  f"наблюдает - {participant.observer_count} {get_suffix(participant.observer_count)}")
        
        print("\n=== Выступающие по порядку ===")
        for round_data in self.rounds:
            print(f"Раунд {round_data['round']}: {round_data['speaker'].full_name}")

    def save_to_file(self, filename: str):
        """Сохраняет распределение ролей в файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== Распределение ролей ===\n")
            for round_data in self.rounds:
                f.write(f"\nРаунд {round_data['round']}\n")
                f.write(f"Выступающий: {round_data['speaker'].full_name}\n")
                f.write(f"Готовящийся: {round_data['preparing'].full_name if round_data['preparing'] else 'нет'}\n")
                listeners = ", ".join([l.full_name for l in round_data['listeners']])
                f.write(f"Слушатели: {listeners}\n")
                observers = ", ".join([o.full_name for o in round_data['observers']])
                f.write(f"Наблюдатели: {observers}\n")

            f.write("\n=== Статистика по участникам ===\n")
            for participant in sorted(self.participants, key=lambda x: x.last_name):
                f.write(f"{participant.full_name}: выступет - {participant.speaker_count} {get_suffix(participant.speaker_count)}, "
                        f"слушает - {participant.listener_count} {get_suffix(participant.listener_count)}, "
                        f"наблюдает - {participant.observer_count} {get_suffix(participant.observer_count)}\n")


def get_suffix(count):
    if count % 10 == 1 and count % 100 != 11:
        return "раз"
    return "раза"


def load_participants_from_file(filename: str) -> List[Participant]:
    """Загружает список участников из файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [Participant(*line.strip().split(maxsplit=1)) for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Ошибка: файл {filename} не найден")
        return []
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        return []


def manual_input_participants() -> List[Participant]:
    """Ручной ввод участников"""
    participants = []
    print("\nВведите участников (имя и фамилия, каждый с новой строки)")
    print("Для завершения ввода оставьте строку пустой\n")

    while True:
        try:
            line = input("Участник: ").strip()
            if not line:
                break
            first_name, last_name = line.split(maxsplit=1)
            participants.append(Participant(first_name, last_name))
        except ValueError:
            print("Ошибка: введите имя и фамилию через пробел")

    return participants


def get_output_filename() -> str:
    """Запрашивает имя файла для сохранения"""
    while True:
        filename = input("\nВведите имя файла для сохранения результатов (или нажмите Enter чтобы пропустить): ").strip()
        if not filename:
            return ""
        if not filename.endswith('.txt'):
            filename += '.txt'
        return filename


def main():
    print("\n=== Вебинарный распределитель ролей ===")

    # Выбор способа ввода участников
    while True:
        choice = input("\nВыберите способ ввода участников:\n"
                       "1 - Загрузить из файла\n"
                       "2 - Ввести вручную\n"
                       "Ваш выбор (1/2): ").strip()
        
        if choice == '1':
            filename = input("Введите имя файла: ").strip()
            participants = load_participants_from_file(filename)
            if participants:
                break
        elif choice == '2':
            participants = manual_input_participants()
            if participants:
                break
        else:
            print("\nНекорректный ввод, попробуйте еще раз")

    if not participants:
        print("\nНет участников для распределения")
        return

    if len(participants) < 5:
        print("\nОшибка: минимальное количество участников - 5")
        return

    # Распределение ролей
    print(f"\nВсего участников: {len(participants)}")
    print(f"Количество наблюдателей в раунде: {2 if len(participants) >= 15 else 1}")

    distributor = WebinarRoleDistributor(participants)

    if distributor.distribute_roles():
        print("\nРезультаты распределения ролей:")
        distributor.print_rounds()
        
        # Сохранение в файл
        filename = get_output_filename()
        if filename:
            distributor.save_to_file(filename)
            print(f"\nРезультаты сохранены в файл: {filename}")
    else:
        print("\nНе удалось распределить роли")


if __name__ == "__main__":
    main()
