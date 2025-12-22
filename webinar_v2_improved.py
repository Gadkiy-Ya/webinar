import random
import sys
from typing import List, Dict, Optional, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RoleType(Enum):
    """Типы ролей в вебинаре"""
    SPEAKER = "speaker"
    LISTENER = "listener"
    OBSERVER = "observer"
    PREPARING = "preparing"

@dataclass
class Participant:
    """Участник вебинара"""
    first_name: str
    last_name: str
    speaker_count: int = 0
    listener_count: int = 0
    observer_count: int = 0
    
    @property
    def full_name(self) -> str:
        """Полное имя участника"""
        return f"{self.first_name} {self.last_name}"
    
    def increment_role_count(self, role: RoleType):
        """Увеличивает счетчик роли"""
        if role == RoleType.SPEAKER:
            self.speaker_count += 1
        elif role == RoleType.LISTENER:
            self.listener_count += 1
        elif role == RoleType.OBSERVER:
            self.observer_count += 1
    
    def get_role_count(self, role: RoleType) -> int:
        """Получает счетчик роли"""
        if role == RoleType.SPEAKER:
            return self.speaker_count
        elif role == RoleType.LISTENER:
            return self.listener_count
        elif role == RoleType.OBSERVER:
            return self.observer_count
        return 0

@dataclass
class Round:
    """Данные одного раунда"""
    round_number: int
    speaker: Participant
    preparing: Optional[Participant] = None
    listeners: List[Participant] = field(default_factory=list)
    observers: List[Participant] = field(default_factory=list)
    
    def get_participants(self) -> List[Participant]:
        """Все участники раунда"""
        participants = [self.speaker]
        if self.preparing:
            participants.append(self.preparing)
        participants.extend(self.listeners)
        participants.extend(self.observers)
        return participants

class ParticipantValidator:
    """Валидация данных участников"""
    
    @staticmethod
    def validate_name(name: str) -> bool:
        """Проверяет корректность имени"""
        return bool(name.strip()) and len(name.strip()) > 0
    
    @staticmethod
    def validate_participant_data(first_name: str, last_name: str) -> bool:
        """Проверяет корректность данных участника"""
        return (ParticipantValidator.validate_name(first_name) and 
                ParticipantValidator.validate_name(last_name))

class RoleDistributor:
    """Основной класс для распределения ролей"""
    
    def __init__(self, participants: List[Participant]):
        self.participants = participants.copy()
        self.rounds: List[Round] = []
        self.current_round = 0
        self.next_speaker: Optional[Participant] = None
        self._setup_configuration()
    
    def _setup_configuration(self):
        """Настройка конфигурации"""
        self.min_participants = 5
        self.max_rounds = len(self.participants)
        self.observers_per_round = 2 if len(self.participants) >= 15 else 1
        self.listeners_per_round = 2
    
    def distribute_roles(self) -> bool:
        """Основной метод распределения ролей"""
        try:
            if not self._validate_participants():
                return False
            
            self.rounds.clear()
            self.current_round = 0
            
            # Выбираем первого выступающего
            first_speaker = self._select_speaker_with_min_count()
            if not first_speaker:
                logger.error("Не удалось выбрать первого выступающего")
                return False
            
            # Начинаем распределение
            self.next_speaker = self._select_preparing_participant(exclude=[first_speaker])
            
            while self._create_next_round():
                continue
            
            # Балансируем роли
            self._balance_roles()
            
            logger.info(f"Успешно создано {len(self.rounds)} раундов")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при распределении ролей: {e}")
            return False
    
    def _validate_participants(self) -> bool:
        """Валидация участников"""
        if len(self.participants) < self.min_participants:
            logger.error(f"Минимальное количество участников: {self.min_participants}")
            return False
        
        # Проверяем, что все участники корректны
        for participant in self.participants:
            if not ParticipantValidator.validate_participant_data(
                participant.first_name, participant.last_name):
                logger.error(f"Некорректные данные участника: {participant.full_name}")
                return False
        
        return True
    
    def _create_next_round(self) -> bool:
        """Создает следующий раунд"""
        if self.current_round >= self.max_rounds:
            return False
        
        speaker = self.next_speaker or self._select_speaker_with_min_count()
        if not speaker:
            return False
        
        preparing = self._select_preparing_participant(exclude=[speaker])
        
        # Выбираем участников для ролей
        exclude_list = [speaker]
        if preparing:
            exclude_list.append(preparing)
        
        listeners = self._select_participants_for_role(
            RoleType.LISTENER, exclude_list, self.listeners_per_round)
        
        if len(listeners) < self.listeners_per_round:
            logger.warning(f"Недостаточно участников для слушателей в раунде {self.current_round + 1}")
            return False
        
        observers = self._select_participants_for_role(
            RoleType.OBSERVER, exclude_list + listeners, self.observers_per_round)
        
        if len(observers) < self.observers_per_round:
            logger.warning(f"Недостаточно участников для наблюдателей в раунде {self.current_round + 1}")
            return False
        
        # Создаем раунд
        round_data = Round(
            round_number=self.current_round + 1,
            speaker=speaker,
            preparing=preparing,
            listeners=listeners,
            observers=observers
        )
        
        # Обновляем счетчики
        speaker.increment_role_count(RoleType.SPEAKER)
        for listener in listeners:
            listener.increment_role_count(RoleType.LISTENER)
        for observer in observers:
            observer.increment_role_count(RoleType.OBSERVER)
        
        self.rounds.append(round_data)
        self.next_speaker = preparing
        self.current_round += 1
        
        return True
    
    def _select_speaker_with_min_count(self) -> Optional[Participant]:
        """Выбирает выступающего с минимальным количеством выступлений"""
        candidates = [p for p in self.participants if p.speaker_count == 0]
        return random.choice(candidates) if candidates else None
    
    def _select_preparing_participant(self, exclude: List[Participant] = None) -> Optional[Participant]:
        """Выбирает готовящегося участника"""
        exclude = exclude or []
        candidates = [p for p in self.participants 
                      if p not in exclude and p.speaker_count == 0]
        return random.choice(candidates) if candidates else None
    
    def _select_participants_for_role(self, role: RoleType, exclude: List[Participant], count: int) -> List[Participant]:
        """Выбирает участников для конкретной роли"""
        exclude = exclude or []
        
        # Сначала выбираем тех, кто еще не был в этой роли
        unserved = [p for p in self.participants 
                    if p not in exclude and p.get_role_count(role) == 0]
        
        if len(unserved) >= count:
            return random.sample(unserved, count)
        
        # Если недостаточно необслуженных, выбираем с минимальным количеством
        available = [p for p in self.participants if p not in exclude]
        available.sort(key=lambda p: p.get_role_count(role))
        
        return available[:count]
    
    def _balance_roles(self):
        """Балансирует роли между участниками"""
        logger.info("Начинаем балансировку ролей")
        
        for participant in self.participants:
            # Балансируем слушателей
            while participant.listener_count == 0:
                if not self._assign_as_listener(participant):
                    break
            
            # Балансируем наблюдателей
            while participant.observer_count == 0:
                if not self._assign_as_observer(participant):
                    break
    
    def _assign_as_listener(self, participant: Participant) -> bool:
        """Назначает участника слушателем"""
        for round_data in self.rounds:
            if self._can_assign_to_round(participant, round_data, RoleType.LISTENER):
                # Находим слушателя с наибольшим количеством раз
                if round_data.listeners:
                    most_experienced = max(round_data.listeners, key=lambda p: p.listener_count)
                    if most_experienced.listener_count > 1:
                        round_data.listeners.remove(most_experienced)
                        most_experienced.listener_count -= 1
                        round_data.listeners.append(participant)
                        participant.listener_count += 1
                        return True
        return False
    
    def _assign_as_observer(self, participant: Participant) -> bool:
        """Назначает участника наблюдателем"""
        for round_data in self.rounds:
            if self._can_assign_to_round(participant, round_data, RoleType.OBSERVER):
                if round_data.observers:
                    most_experienced = max(round_data.observers, key=lambda p: p.observer_count)
                    if most_experienced.observer_count > 1 or participant.observer_count == 0:
                        round_data.observers.remove(most_experienced)
                        most_experienced.observer_count -= 1
                        round_data.observers.append(participant)
                        participant.observer_count += 1
                        return True
        return False
    
    def _can_assign_to_round(self, participant: Participant, round_data: Round, role: RoleType) -> bool:
        """Проверяет, можно ли назначить участника в раунд"""
        if participant in round_data.get_participants():
            return False
        
        if role == RoleType.LISTENER:
            return len(round_data.listeners) > 0
        elif role == RoleType.OBSERVER:
            return len(round_data.observers) > 0
        
        return False

class WebinarFormatter:
    """Форматирование и вывод результатов"""
    
    @staticmethod
    def get_suffix(count: int) -> str:
        """Возвращает правильное окончание для слова 'раз'"""
        if count % 10 == 1 and count % 100 != 11:
            return "раз"
        return "раза"
    
    @staticmethod
    def print_rounds(rounds: List[Round]):
        """Выводит результаты распределения"""
        print("\n=== Распределение ролей ===")
        for round_data in rounds:
            print(f"\nРаунд {round_data.round_number}")
            print(f"Выступающий: {round_data.speaker.full_name}")
            print(f"Готовящийся: {round_data.preparing.full_name if round_data.preparing else 'нет'}")
            
            listeners = ", ".join([l.full_name for l in round_data.listeners])
            print(f"Слушатели: {listeners}")
            
            observers = ", ".join([o.full_name for o in round_data.observers])
            print(f"Наблюдатели: {observers}")
    
    @staticmethod
    def print_statistics(participants: List[Participant]):
        """Выводит статистику по участникам"""
        print("\n=== Статистика по участникам ===")
        for participant in sorted(participants, key=lambda x: x.last_name):
            speaker_suffix = WebinarFormatter.get_suffix(participant.speaker_count)
            listener_suffix = WebinarFormatter.get_suffix(participant.listener_count)
            observer_suffix = WebinarFormatter.get_suffix(participant.observer_count)
            
            print(f"{participant.full_name}: "
                  f"выступает - {participant.speaker_count} {speaker_suffix}, "
                  f"слушает - {participant.listener_count} {listener_suffix}, "
                  f"наблюдает - {participant.observer_count} {observer_suffix}")
    
    @staticmethod
    def print_speakers_order(rounds: List[Round]):
        """Выводит порядок выступлений"""
        print("\n=== Выступающие по порядку ===")
        for round_data in rounds:
            print(f"Раунд {round_data.round_number}: {round_data.speaker.full_name}")

class FileManager:
    """Работа с файлами"""
    
    @staticmethod
    def load_participants(filename: str) -> List[Participant]:
        """Загружает участников из файла"""
        filename = filename + '.txt'
        logger.info(f"Загрузка участников из файла: {filename}")
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                participants = []
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        parts = line.split(maxsplit=1)
                        if len(parts) != 2:
                            logger.warning(f"Строка {line_num}: ожидается 'имя фамилия', получено '{line}'")
                            continue
                        
                        first_name, last_name = parts
                        if ParticipantValidator.validate_participant_data(first_name, last_name):
                            participants.append(Participant(first_name, last_name))
                        else:
                            logger.warning(f"Строка {line_num}: некорректные данные участника")
                    
                    except Exception as e:
                        logger.warning(f"Строка {line_num}: ошибка обработки - {e}")
                        continue
                
                logger.info(f"Загружено {len(participants)} участников")
                return participants
                
        except FileNotFoundError:
            logger.error(f"Файл {filename} не найден")
            return []
        except Exception as e:
            logger.error(f"Ошибка при чтении файла: {e}")
            return []
    
    @staticmethod
    def save_results(rounds: List[Round], participants: List[Participant], filename: str):
        """Сохраняет результаты в файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=== Распределение ролей ===\n")
                for round_data in rounds:
                    f.write(f"\nРаунд {round_data.round_number}\n")
                    f.write(f"Выступающий: {round_data.speaker.full_name}\n")
                    f.write(f"Готовящийся: {round_data.preparing.full_name if round_data.preparing else 'нет'}\n")
                    
                    listeners = ", ".join([l.full_name for l in round_data.listeners])
                    f.write(f"Слушатели: {listeners}\n")
                    
                    observers = ", ".join([o.full_name for o in round_data.observers])
                    f.write(f"Наблюдатели: {observers}\n")
                
                f.write("\n=== Статистика по участникам ===\n")
                for participant in sorted(participants, key=lambda x: x.last_name):
                    speaker_suffix = WebinarFormatter.get_suffix(participant.speaker_count)
                    listener_suffix = WebinarFormatter.get_suffix(participant.listener_count)
                    observer_suffix = WebinarFormatter.get_suffix(participant.observer_count)
                    
                    f.write(f"{participant.full_name}: "
                           f"выступает - {participant.speaker_count} {speaker_suffix}, "
                           f"слушает - {participant.listener_count} {listener_suffix}, "
                           f"наблюдает - {participant.observer_count} {observer_suffix}\n")
            
            logger.info(f"Результаты сохранены в файл: {filename}")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении файла: {e}")

class WebinarApp:
    """Основное приложение"""
    
    def __init__(self):
        self.participants: List[Participant] = []
    
    def run(self):
        """Запуск приложения"""
        print("\n=== Вебинарный распределитель ролей (улучшенная версия) ===")
        
        while True:
            choice = self._get_main_menu_choice()
            
            if choice == '1':
                self._load_from_file()
            elif choice == '2':
                self._manual_input()
            elif choice == '3':
                self._show_participants()
            elif choice == '4':
                self._delete_participant()
            elif choice == '5':
                self._distribute_roles()
            elif choice == '6':
                print("До свидания!")
                sys.exit()
            else:
                print("Некорректный ввод, попробуйте еще раз")
    
    def _get_main_menu_choice(self) -> str:
        """Получает выбор пользователя в главном меню"""
        return input("\nВыберите действие:\n"
                    "1 - Загрузить из файла\n"
                    "2 - Ввести вручную\n"
                    "3 - Показать список участников\n"
                    "4 - Удалить участника\n"
                    "5 - Распределить роли\n"
                    "6 - Выход\n"
                    "Ваш выбор: ").strip()
    
    def _load_from_file(self):
        """Загрузка участников из файла"""
        filename = input("Введите имя файла: ").strip()
        if filename:
            self.participants = FileManager.load_participants(filename)
    
    def _manual_input(self):
        """Ручной ввод участников"""
        print("\nВведите участников (имя и фамилия, каждый с новой строки)")
        print("Для завершения ввода оставьте строку пустой\n")
        
        participants = []
        while True:
            line = input("Участник: ").strip()
            if not line:
                break
            
            try:
                first_name, last_name = line.split(maxsplit=1)
                if ParticipantValidator.validate_participant_data(first_name, last_name):
                    participants.append(Participant(first_name, last_name))
                    print(f"Добавлен: {first_name} {last_name}")
                else:
                    print("Ошибка: некорректные данные участника")
            except ValueError:
                print("Ошибка: введите имя и фамилию через пробел")
        
        self.participants = participants
        print(f"\nДобавлено {len(participants)} участников")
    
    def _show_participants(self):
        """Показывает список участников"""
        if not self.participants:
            print("\n=== Список участников пуст ===")
            return
        
        print("\n=== Список участников ===")
        for i, participant in enumerate(self.participants, start=1):
            print(f"{i}. {participant.full_name}")
    
    def _delete_participant(self):
        """Удаляет участника"""
        if not self.participants:
            print("Список участников пуст")
            return
        
        try:
            self._show_participants()
            index = int(input("\nВведите номер участника для удаления: ")) - 1
            
            if 0 <= index < len(self.participants):
                removed = self.participants.pop(index)
                print(f"Удален участник: {removed.full_name}")
            else:
                print("Ошибка: неверный номер участника")
        except ValueError:
            print("Ошибка: введите корректный номер")
    
    def _distribute_roles(self):
        """Распределяет роли"""
        if not self.participants:
            print("Нет участников для распределения")
            return
        
        print(f"\nВсего участников: {len(self.participants)}")
        print(f"Количество наблюдателей в раунде: {2 if len(self.participants) >= 15 else 1}")
        
        distributor = RoleDistributor(self.participants)
        
        if distributor.distribute_roles():
            # Выводим результаты
            WebinarFormatter.print_rounds(distributor.rounds)
            WebinarFormatter.print_statistics(self.participants)
            WebinarFormatter.print_speakers_order(distributor.rounds)
            
            # Сохранение в файл
            filename = self._get_output_filename()
            if filename:
                FileManager.save_results(distributor.rounds, self.participants, filename)
                print(f"\nРезультаты сохранены в файл: {filename}")
        else:
            print("\nНе удалось распределить роли")
    
    def _get_output_filename(self) -> str:
        """Получает имя файла для сохранения"""
        filename = input("\nВведите имя файла для сохранения (или нажмите Enter): ").strip()
        if filename and not filename.endswith('.txt'):
            filename += '.txt'
        return filename

def main():
    """Главная функция"""
    try:
        app = WebinarApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print("Произошла критическая ошибка. Проверьте логи для подробностей.")

if __name__ == "__main__":
    main()