"""This is the main module that contains views and the main logic"""

# Libraries
import curses
import calendar
import time

# Modules
from calcure.calendars import Calendar
from calcure.configuration import cf
from calcure.weather import Weather
from calcure.repository import Importer, FileRepository
from calcure.dialogues import clear_line
from calcure.screen import Screen
from calcure.data import *
from calcure.translation_en import *
from calcure.controls import *


__version__ = "2.0.0"


def initialize_colors():
    """Define all the color pairs"""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(Color.DAY_NAMES.value, cf.COLOR_DAY_NAMES, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.WEEKENDS.value, cf.COLOR_WEEKENDS, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.HINTS.value, cf.COLOR_HINTS, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.TODAY.value, cf.COLOR_TODAY, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.DAYS.value, cf.COLOR_DAYS, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.WEEKEND_NAMES.value, cf.COLOR_WEEKEND_NAMES, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.BIRTHDAYS.value, cf.COLOR_BIRTHDAYS, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.PROMPTS.value, cf.COLOR_PROMPTS, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.CONFIRMATIONS.value, cf.COLOR_CONFIRMATIONS, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.TITLE.value, cf.COLOR_TITLE, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.TODO.value, cf.COLOR_TODO, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.DONE.value, cf.COLOR_DONE, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.IMPORTANT.value, cf.COLOR_IMPORTANT, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.TIMER.value, cf.COLOR_TIMER, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.TIMER_PAUSED.value, cf.COLOR_TIMER_PAUSED, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.HOLIDAYS.value, cf.COLOR_HOLIDAYS, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.EVENTS.value, cf.COLOR_EVENTS, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.TIME.value, cf.COLOR_TIME, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.WEATHER.value, cf.COLOR_WEATHER, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.UNIMPORTANT.value, cf.COLOR_UNIMPORTANT, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.CALENDAR_HEADER.value, cf.COLOR_CALENDAR_HEADER, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.ACTIVE_PANE.value, cf.COLOR_ACTIVE_PANE, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.SEPARATOR.value, cf.COLOR_SEPARATOR, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.EMPTY.value, cf.COLOR_BACKGROUND, cf.COLOR_BACKGROUND)
    curses.init_pair(Color.CALENDAR_BOARDER.value, cf.COLOR_CALENDAR_BOARDER, cf.COLOR_BACKGROUND)

    if not cf.MINIMAL_WEEKEND_INDICATOR:
        curses.init_pair(Color.WEEKENDS.value, curses.COLOR_BLACK, cf.COLOR_WEEKENDS)
    if not cf.MINIMAL_TODAY_INDICATOR:
        curses.init_pair(Color.TODAY.value, curses.COLOR_BLACK, cf.COLOR_TODAY)
    if not cf.MINIMAL_DAYS_INDICATOR:
        curses.init_pair(Color.DAYS.value, curses.COLOR_BLACK, cf.COLOR_DAYS)


class View:
    """Parent class of a view that displays things at certain coordinates"""

    def __init__(self, stdscr, y, x):
        self.stdscr = stdscr
        self.y = y
        self.x = x

    def fill_background(self):
        """Fill the screen background with background color"""
        y_max, x_max = self.stdscr.getmaxyx()
        for index in range(y_max - 1):
            self.stdscr.addstr(index, 0, " " * x_max, curses.color_pair(1))

    def display_line(self, y, x, text, color, bold=False, underlined=False):
        """Display the line of text respecting the slyling and available space"""

        # Make sure that we display inside the screen:
        y_max, x_max = self.stdscr.getmaxyx()
        if y >= y_max or x >= x_max:
            return

        # Cut the text if it does not fit the screen:
        text = text[:(x_max - 1 - x)]

        if bold and underlined:
            self.stdscr.addstr(y, x, text, curses.color_pair(color.value) | curses.A_BOLD | curses.A_UNDERLINE)
        elif bold and not underlined:
            self.stdscr.addstr(y, x, text, curses.color_pair(color.value) | curses.A_BOLD)
        elif underlined and not bold:
            self.stdscr.addstr(y, x, text, curses.color_pair(color.value) | curses.A_UNDERLINE)
        else:
            self.stdscr.addstr(y, x, text, curses.color_pair(color.value))


class TaskView(View):
    """Display a single task"""

    def __init__(self, stdscr, y, x, task, screen):
        super().__init__(stdscr, y, x)
        self.task = task
        self.screen = screen
        self.info = f'{self.icon} {self.task.name[self.indent:]}'

    @property
    def color(self):
        """Select the color depending on the status"""
        color = Color.TODO
        if self.task.status == Status.DONE:
            color = Color.DONE
        if self.task.status == Status.IMPORTANT:
            color = Color.IMPORTANT
        if self.task.status == Status.UNIMPORTANT:
            color = Color.UNIMPORTANT
        return color

    @property
    def icon(self):
        """Select the icon for the task"""
        icon = cf.TODO_ICON
        if cf.DISPLAY_ICONS:
            for keyword in cf.ICONS:
                if keyword in self.task.name.lower():
                    icon = cf.ICONS[keyword]
        if self.task.status == Status.DONE:
            icon = cf.DONE_ICON
        if self.task.status == Status.IMPORTANT:
            icon = cf.IMPORTANT_ICON
        return icon

    @property
    def indent(self):
        """Calculate the left indentation depending on the task level"""
        if self.task.name[:4] == '----':
            return 4
        if self.task.name[:2] == '--':
            return 2
        return 0

    def obfuscate_info(self):
        """Obfuscate the info if privacy mode is on"""
        self.info = f'{cf.TODO_ICON} {cf.PRIVACY_ICON * len(self.task.name[self.indent:])}'

    def render(self):
        """Render a line with an icon, task, and timer"""
        if self.screen.privacy or self.task.privacy:
            self.obfuscate_info()
        self.display_line(self.y, self.x + self.indent, self.info, self.color)
        timer_indentation = self.screen.x_min + 2 + len(self.info) + self.indent
        timer_view = TimerView(self.stdscr, self.y, timer_indentation, self.task.timer)
        timer_view.render()


class TimerView(View):
    """Display a single task"""

    def __init__(self, stdscr, y, x, timer):
        super().__init__(stdscr, y, x)
        self.timer = timer

    @property
    def color(self):
        """Select the color depending on the timer status"""
        color = Color.TIMER if self.timer.is_counting else Color.TIMER_PAUSED
        return color

    @property
    def icon(self):
        """Return icon corresponding to timer state"""
        if not self.timer.is_counting and cf.DISPLAY_ICONS:
            icon = "⏯︎ "
        elif self.timer.is_counting and cf.DISPLAY_ICONS:
            icon = "⏵ "
        else:
            icon = ''
        return icon

    def render(self):
        """Render a line with a timer and icon"""
        if self.timer.is_started:
            time_string = self.icon + self.timer.passed_time
            self.display_line(self.y, self.x, time_string, self.color)


class JournalView(View):
    """Displays a list of all tasks"""

    def __init__(self, stdscr, y, x, user_tasks, screen):
        super().__init__(stdscr, y, x)
        self.user_tasks = user_tasks
        self.screen = screen

    def render(self):
        """Render the list of tasks"""
        if not self.user_tasks.items and cf.SHOW_NOTHING_PLANNED:
            self.display_line(self.y, self.x, MSG_TS_NOTHING, Color.UNIMPORTANT)
        for index, task in enumerate(self.user_tasks.items):
            task_view = TaskView(self.stdscr, self.y, self.x, task, self.screen)
            task_view.render()
            if self.screen.selection_mode:
                self.display_line(self.y, self.x, str(index + 1), Color.TODAY)
            self.y += 1


class EventView(View):
    """Parent class to display events"""

    def __init__(self, stdscr, y, x, event, screen):
        super().__init__(stdscr, y, x)
        self.event = event
        self.screen = screen
        self.info = f"{self.icon} {self.event.name}"

    @property
    def icon(self):
        """Select the right icon for the event"""
        return cf.EVENT_ICON

    @property
    def color(self):
        """Select the color depending on the status and type"""
        color = Color.EVENTS
        if self.event.status == Status.IMPORTANT:
            color = Color.IMPORTANT
        if self.event.status == Status.UNIMPORTANT:
            color = Color.UNIMPORTANT
        return color

    def obfuscate_info(self):
        """Obfuscate the info if privacy mode is on"""
        self.info = f'{cf.EVENT_ICON} {cf.PRIVACY_ICON * len(self.event.name)}'

    def cut_info(self):
        """Cut the name to fit into the cell of the calendar"""
        self.info = self.info[:self.screen.x_max - self.x]
        x_cell = self.screen.x_max // 7
        if (cf.CUT_TITLES or cf.SHOW_CALENDAR_BOARDERS) and self.screen.calendar_state == CalState.MONTHLY:
            self.info = self.info[:(x_cell - 1)]

    def minimize_info(self):
        """Reduce the info to just icon if not much space if available"""
        x_cell = self.screen.x_max // 7
        if x_cell < 7:
            self.info = self.icon

    def fill_remaining_space(self):
        """Fill rest of the line of the calendar with empty characters"""
        x_cell = self.screen.x_max // 7
        if len(self.info) < self.screen.x_max - self.x:
            self.info += " "*(self.screen.x_max - self.x - len(self.info))


class UserEventView(EventView):
    """Display a single user event"""

    @property
    def icon(self):
        """Select the right icon for the event"""
        icon = cf.EVENT_ICON
        if cf.DISPLAY_ICONS:
            for keyword in cf.ICONS:
                if keyword in self.event.name.lower():
                    icon = cf.ICONS[keyword]
        if self.screen.privacy or self.event.privacy:
            icon = cf.PRIVACY_ICON
        return icon

    def render(self):
        """Render this view on the screen"""
        if self.screen.privacy or self.event.privacy:
            self.obfuscate_info()
        self.fill_remaining_space()
        self.cut_info()
        self.minimize_info()
        self.display_line(self.y, self.x, self.info, self.color)


class BirthdayView(EventView):
    """Display a line with birthday icon and name"""

    @property
    def icon(self):
        """Set the icon for birthdays"""
        return cf.BIRTHDAY_ICON

    def render(self):
        """Render this view on the screen"""
        if self.screen.privacy:
            self.obfuscate_info()
        self.fill_remaining_space()
        self.cut_info()
        self.minimize_info()
        self.display_line(self.y, self.x, self.info, Color.BIRTHDAYS)


class HolidayView(EventView):
    """Display a line with holiday icon and occasion"""

    @property
    def icon(self):
        """Set the icon for holiday events"""
        return cf.HOLIDAY_ICON

    def render(self):
        """Render this view on the screen"""
        self.fill_remaining_space()
        self.cut_info()
        self.minimize_info()
        self.display_line(self.y, self.x, self.info, Color.HOLIDAYS)


class DailyView(View):
    """Display all events occurring on this days"""

    def __init__(self, stdscr, y, x, repeated_user_events, user_events, holidays, birthdays, screen, index_offset):
        super().__init__(stdscr, y, x)
        self.repeated_user_events = repeated_user_events.filter_events_that_day(screen)
        self.user_events = user_events.filter_events_that_day(screen)
        self.holidays = holidays.filter_events_that_day(screen)
        self.birthdays = birthdays.filter_events_that_day(screen)
        self.screen = screen
        self.index_offset = index_offset
        self.y_cell = (self.screen.y_max - 3) // 6
        self.x_cell = self.screen.x_max // 7
        self.hidden_events_sign = cf.HIDDEN_ICON + " "*(self.x_cell-len(cf.HIDDEN_ICON))

    def render(self):
        """Render this view on the screen"""
        index = 0

        # Show user events:
        for event in self.user_events.items:
            if index < self.y_cell - 1:
                user_event_view = UserEventView(self.stdscr, self.y + index, self.x, event, self.screen)
                user_event_view.render()
                if self.screen.selection_mode:
                    self.display_line(self.y + index, self.x, str(index + self.index_offset + 1), Color.TODAY)
            else:
                self.display_line(self.y + self.y_cell - 2, self.x, self.hidden_events_sign, Color.EVENTS)
            index += 1

        # Show repeated user events:
        for event in self.repeated_user_events.items:
            if index < self.y_cell - 1:
                user_event_view = UserEventView(self.stdscr, self.y + index, self.x, event, self.screen)
                user_event_view.render()
            else:
                self.display_line(self.y + self.y_cell - 2, self.x, self.hidden_events_sign, Color.EVENTS)
            index += 1

        # Show holidays:
        if not cf.DISPLAY_HOLIDAYS:
            return
        for event in self.holidays.items:
            if index < self.y_cell - 1:
                holiday_view = HolidayView(self.stdscr, self.y + index, self.x, event, self.screen)
                holiday_view.render()
            else:
                self.display_line(self.y + self.y_cell - 2, self.x, self.hidden_events_sign, Color.HOLIDAYS)
            index += 1

        # Show birthdays:
        if not cf.BIRTHDAYS_FROM_ABOOK:
            return
        for event in self.birthdays.items:
            if index < self.y_cell - 1:
                birthday_view = BirthdayView(self.stdscr, self.y + index, self.x, event, self.screen)
                birthday_view.render()
            else:
                self.display_line(self.y + self.y_cell - 2, self.x, self.hidden_events_sign, Color.BIRTHDAYS)
            index += 1

        if index == 0 and self.screen.calendar_state == CalState.DAILY and cf.SHOW_NOTHING_PLANNED:
            self.display_line(self.y, self.x, MSG_TS_NOTHING, Color.UNIMPORTANT)


class DayNumberView(View):
    """Display the date of the day in month with proper styling"""

    def __init__(self, stdscr, y, x, screen, day, day_in_week, x_cell):
        super().__init__(stdscr, y, x)
        self.screen = screen
        self.day = day
        self.day_in_week = day_in_week
        self.x_cell = x_cell
        self.screen.day = self.day

    def render(self):
        """Render this view on the screen"""
        if self.screen.date == self.screen.today:
            today = f"{self.day}{cf.TODAY_ICON}{' '*(self.x_cell - len(str(self.day)) - 2)}"
            self.display_line(self.y, self.x, today, Color.TODAY, cf.BOLD_TODAY, cf.UNDERLINED_TODAY)
        elif self.day_in_week + 1 in cf.WEEKEND_DAYS:
            weekend = f"{self.day}{' '*(self.x_cell - len(str(self.day)) - 1)}"
            self.display_line(self.y, self.x, weekend, Color.WEEKENDS, cf.BOLD_WEEKENDS, cf.UNDERLINED_WEEKENDS)
        else:
            weekday = f"{self.day}{' '*(self.x_cell - len(str(self.day)) - 1)}"
            self.display_line(self.y, self.x, weekday, Color.DAYS, cf.BOLD_DAYS, cf.UNDERLINED_DAYS)


class TitleView(View):
    """Show the title in the header"""

    def __init__(self, stdscr, y, x, title, screen):
        super().__init__(stdscr, y, x)
        self.title = title
        self.screen = screen

    def render(self):
        """Render this view on the screen"""
        if self.screen.active_pane and self.screen.split:
            self.display_line(0, self.screen.x_min, self.title, Color.ACTIVE_PANE, cf.BOLD_ACTIVE_PANE, cf.UNDERLINED_ACTIVE_PANE)
        else:
            self.display_line(0, self.screen.x_min, self.title, Color.CALENDAR_HEADER, cf.BOLD_TITLE, cf.UNDERLINED_TITLE)


class HeaderView(View):
    """Show the header that includes the weather, time, and title"""

    def __init__(self, stdscr, y, x, title, weather, screen):
        super().__init__(stdscr, y, x)
        self.title = title
        self.weather = weather
        self.screen = screen

    def render(self):
        _, x_max = self.stdscr.getmaxyx()

        # Show title:
        title_view = TitleView(self.stdscr, 0, self.screen.x_min, self.title, self.screen)
        title_view.render()

        if self.screen.state == AppState.JOURNAL and self.screen.split:
            return

        # Show weather is space allows and it is loaded:
        size_allows = len(self.weather.forcast) < self.screen.x_max - len(self.title)
        if cf.SHOW_WEATHER and size_allows:
            self.display_line(0, self.screen.x_max - len(self.weather.forcast) - 1, self.weather.forcast, Color.WEATHER)

        # Show time:
        time_string = time.strftime("%H:%M", time.localtime())
        size_allows = len(self.weather.forcast) < self.screen.x_max - len(self.title) - len(time_string)
        if cf.SHOW_CURRENT_TIME and size_allows:
            self.display_line(0, (self.screen.x_max // 2 - 2), time_string, Color.TIME)


class FooterView(View):
    """Display the footer with keybinding"""

    def __init__(self, stdscr, y, x, screen):
        super().__init__(stdscr, y, x)
        self.screen = screen

    def render(self):
        if not cf.SHOW_KEYBINDINGS: return
        clear_line(self.stdscr, self.screen.y_max - 1)
        if self.screen.state == AppState.CALENDAR:
            if self.screen.calendar_state == CalState.MONTHLY:
                hint = CALENDAR_HINT
            else:
                hint = CALENDAR_HINT_D
        elif self.screen.state == AppState.JOURNAL:
            hint = JOURNAL_HINT
        self.display_line(self.screen.y_max - 1, 0, hint, Color.HINTS)


class SeparatorView(View):
    """Display the separator in the split screen"""

    def __init__(self, stdscr, y, x, screen):
        super().__init__(stdscr, y, x)
        self.screen = screen

    def render(self):
        _, x_max = self.stdscr.getmaxyx()
        x_separator = x_max - self.screen.journal_pane_width
        y_cell = (self.screen.y_max - 3) // 6
        height = 6*y_cell + 2 if cf.SHOW_CALENDAR_BOARDERS else self.screen.y_max
        for row in range(height):
            self.display_line(row, x_separator, cf.SEPARATOR_ICON, Color.SEPARATOR)

        if cf.SHOW_CALENDAR_BOARDERS and self.screen.calendar_state == CalState.MONTHLY:
            for row in range(1, 7):
                self.display_line(row*y_cell + 1, x_separator, "┤", Color.CALENDAR_BOARDER)
            self.display_line(6*y_cell + 1, x_separator, "┘", Color.CALENDAR_BOARDER)


class CalenarBoarderView(View):
    """Display the boarders in the monthly view"""

    def __init__(self, stdscr, y, x, screen):
        super().__init__(stdscr, y, x)
        self.screen = screen

    def render(self):
        x_cell = self.screen.x_max // 7
        y_cell = (self.screen.y_max - 3) // 6

        # Vertical lines:
        for column in range(1, 7):
            for row in range(y_cell*6):
                self.display_line(row + 2, column*x_cell - 1, "│", Color.CALENDAR_BOARDER)

        # Horizontal lines:
        for row in range(1, 7):
            for column in range(0, self.screen.x_max):
                self.display_line(row*y_cell + 1, column, "─", Color.CALENDAR_BOARDER)

        # Connectors:
        for row in range(1, 6):
            for column in range(1, 7):
                self.display_line(row*y_cell + 1, column*x_cell - 1, "┼", Color.CALENDAR_BOARDER)
        for column in range(1, 7):
            self.display_line(6*y_cell + 1, column*x_cell - 1, "┴", Color.CALENDAR_BOARDER)


class DaysNameView(View):
    """Display day name depending on the screen available and with right style"""

    def __init__(self, stdscr, y, x, screen):
        super().__init__(stdscr, y, x)
        self.screen = screen

    def render(self):
        num = 2 if self.screen.x_max < 80 else 10
        x_cell = int(self.screen.x_max // 7)

        # Depending on which day we start the week, weekends are shifted:
        for i in range(7):
            shift = cf.START_WEEK_DAY - 1
            day_number = i + shift - 7*((i + shift) > 6)
            day_names = DAYS_PERSIAN if cf.USE_PERSIAN_CALENDAR else DAYS
            name = day_names[day_number][:num]
            x = self.x + i*x_cell
            if day_number + 1 not in cf.WEEKEND_DAYS:
                self.display_line(self.y, x, name, Color.DAY_NAMES, cf.BOLD_DAY_NAMES, cf.UNDERLINED_DAY_NAMES)
            else:
                self.display_line(self.y, x, name, Color.WEEKEND_NAMES, cf.BOLD_WEEKEND_NAMES, cf.UNDERLINED_WEEKEND_NAMES)


##################### SCREENS ##########################


class DailyScreenView(View):
    """Daily view showing events of the day"""

    def __init__(self, stdscr, y, x, weather, user_events, holidays, birthdays, screen):
        super().__init__(stdscr, y, x)
        self.weather = weather
        self.user_events = user_events
        self.holidays = holidays
        self.birthdays = birthdays
        self.screen = screen

    def render(self):
        self.screen.state = AppState.CALENDAR
        if self.screen.x_max < 6 or self.screen.y_max < 3: return
        # self.fill_background()
        curses.halfdelay(255)

        # Form a string with month, year, and day with today icon:
        month_names = MONTHS_PERSIAN if cf.USE_PERSIAN_CALENDAR else MONTHS
        icon = cf.TODAY_ICON if self.screen.date == self.screen.today else ''
        month_string = str(month_names[self.screen.month-1])
        date_string = f'{month_string} {self.screen.day}, {self.screen.year} {icon}'

        # Display header and footer:
        header_view = HeaderView(self.stdscr, 0, 0, date_string, self.weather, self.screen)
        header_view.render()

        # Display the events:
        repeated_user_events = RepeatedEvents(self.user_events, cf.USE_PERSIAN_CALENDAR)
        daily_view = DailyView(self.stdscr, self.y + 2, self.x, repeated_user_events,
                               self.user_events, self.holidays, self.birthdays, self.screen, 0)
        daily_view.render()


class MonthlyScreenView(View):
    """Monthly view showing events of the month"""

    def __init__(self, stdscr, y, x, weather, user_events, holidays, birthdays, screen):
        super().__init__(stdscr, y, x)
        self.weather = weather
        self.user_events = user_events
        self.holidays = holidays
        self.birthdays = birthdays
        self.screen = screen

    def render(self):
        self.screen.state = AppState.CALENDAR
        if self.screen.x_max < 6 or self.screen.y_max < 3: return
        curses.halfdelay(100)

        # Info about the month:
        month_names = MONTHS_PERSIAN if cf.USE_PERSIAN_CALENDAR else MONTHS
        month_year_string = month_names[self.screen.month-1] + " " + str(self.screen.year)
        dates = Calendar(cf.START_WEEK_DAY - 1, cf.USE_PERSIAN_CALENDAR).monthdayscalendar(self.screen.year, self.screen.month)

        y_cell = (self.screen.y_max - 3) // 6
        x_cell = self.screen.x_max // 7

        header_view = HeaderView(self.stdscr, 0, 0, month_year_string, self.weather, self.screen)
        days_name_view = DaysNameView(self.stdscr, 1, 0, self.screen)
        header_view.render()
        days_name_view.render()

        # Displaying the dates and events:
        repeated_user_events = RepeatedEvents(self.user_events, cf.USE_PERSIAN_CALENDAR)
        num_events_this_month = 0
        for row, week in enumerate(dates):
            for col, day in enumerate(week):
                if day != 0:
                    # Display dates of the month with proper styles:
                    day_in_week = col + (cf.START_WEEK_DAY - 1) - 7 * ((col + (cf.START_WEEK_DAY - 1)) > 6)
                    day_number_view = DayNumberView(self.stdscr, 2 + row * y_cell, col * x_cell, self.screen, day, day_in_week, x_cell)
                    day_number_view.render()

                    # Display the events:
                    self.screen.day = day
                    daily_view = DailyView(self.stdscr, 3 + row * y_cell, col * x_cell, repeated_user_events,
                                           self.user_events, self.holidays, self.birthdays, self.screen, num_events_this_month)
                    daily_view.render()
                    num_events_this_month += len(self.user_events.filter_events_that_day(self.screen).items)

        if cf.SHOW_CALENDAR_BOARDERS:
            calendar_boarder_view = CalenarBoarderView(self.stdscr, 0, 0, self.screen)
            calendar_boarder_view.render()


class JournalScreenView(View):
    def __init__(self, stdscr, y, x, weather, user_tasks, screen):
        super().__init__(stdscr, y, x)
        self.weather = weather
        self.user_tasks = user_tasks
        self.screen = screen
        self.refresh_time = 100

    def calculate_refresh_rate(self):
        """Check if a timer is running and change the refresh rate"""
        for task in self.user_tasks.items:
            if task.timer.is_counting:
                self.refresh_time = cf.REFRESH_INTERVAL * 10
                self.screen.refresh_now = False
                break

    def render(self):
        """Journal view showing all tasks"""
        self.screen.state = AppState.JOURNAL
        if self.screen.x_max < 6 or self.screen.y_max < 3:
            return

        # Check if any of the timers is counting, and increase the update time:
        self.calculate_refresh_rate()
        curses.halfdelay(self.refresh_time)

        # Display header and footer:
        header_view = HeaderView(self.stdscr, 0, 0, cf.JOURNAL_HEADER, self.weather, self.screen)
        header_view.render()

        # Display the tasks:
        journal_view = JournalView(self.stdscr, 2, self.screen.x_min, self.user_tasks, self.screen)
        journal_view.render()


class HelpScreenView(View):
    """Help screen displaying information about keybindings"""

    def __init__(self, stdscr, y, x, screen):
        super().__init__(stdscr, y, x)
        self.screen = screen

    def calibrate_position(self):
        """Depending on the screen space calculate the best position"""
        self.y_max, self.x_max = self.stdscr.getmaxyx()

        if self.x_max < 102:
            self.global_shift_x = 0
            self.shift_x = 0
            self.shift_y = 6 + len(KEYS_GENERAL) + len(KEYS_CALENDAR)
        else:
            self.global_shift_x = (self.x_max - 102) // 2
            self.shift_x = 45
            self.shift_y = 2

        if self.y_max > 20 and self.x_max >= 102:
            self.global_shift_y = (self.y_max - 20) // 2
        else:
            self.global_shift_y = 0

    def render(self):
        """Draw the help screen"""
        self.calibrate_position()
        if self.x_max < 6 or self.y_max < 3:
            return
        curses.halfdelay(255)
        self.stdscr.clear()
        self.fill_background()

        # Left column:
        self.display_line(self.global_shift_y, self.global_shift_x + 1, f"{MSG_NAME} {__version__}",
                            Color.ACTIVE_PANE, cf.BOLD_TITLE, cf.UNDERLINED_TITLE)
        self.display_line(self.global_shift_y + 2, self.global_shift_x + 8,
                          TITLE_KEYS_GENERAL, Color.TITLE, cf.BOLD_TITLE, cf.UNDERLINED_TITLE)
        for index, key in enumerate(KEYS_GENERAL):
            line = f"{key} {KEYS_GENERAL[key]}"
            self.display_line(self.global_shift_y + index + 3, self.global_shift_x, line, Color.TODO)

        self.display_line(self.global_shift_y + 4 + len(KEYS_GENERAL), self.global_shift_x + 8,
                          TITLE_KEYS_CALENDAR, Color.TITLE, cf.BOLD_TITLE, cf.UNDERLINED_TITLE)
        for index, key in enumerate(KEYS_CALENDAR):
            line = f"{key} {KEYS_CALENDAR[key]}"
            self.display_line(self.global_shift_y + index + 5 + len(KEYS_GENERAL), self.global_shift_x, line, Color.TODO)

        # Right column:
        d_x = self.global_shift_x + self.shift_x
        d_y = self.global_shift_y + self.shift_y
        self.display_line(d_y, d_x + 8, TITLE_KEYS_JOURNAL, Color.TITLE, cf.BOLD_TITLE, cf.UNDERLINED_TITLE)
        for index, key in enumerate(KEYS_TODO):
            line = f"{key} {KEYS_TODO[key]}"
            self.display_line(d_y + index + 1, d_x, line, Color.TODO)

        # Additional info:
        d_x = self.global_shift_x + self.shift_x + 8
        d_y = self.global_shift_y + len(KEYS_TODO) + self.shift_y
        self.display_line(d_y + 2, d_x, MSG_VIM, Color.ACTIVE_PANE)
        self.display_line(d_y + 4, d_x, MSG_INFO, Color.TODO)
        self.display_line(d_y + 5, d_x, MSG_SITE, Color.TITLE)


def main(stdscr) -> None:
    """Main function that runs and switches screens"""

    # Load the data:
    weather = Weather(cf.WEATHER_CITY)
    if cf.SHOW_WEATHER:
        print("Weather is loading...")
        weather.load_from_wttr()
    screen = Screen(stdscr, cf.PRIVACY_MODE, cf.DEFAULT_VIEW, cf.SPLIT_SCREEN, cf.RIGHT_PANE_PERCENTAGE, cf.USE_PERSIAN_CALENDAR)
    file_repository = FileRepository(cf.TASKS_FILE, cf.EVENTS_FILE, cf.HOLIDAY_COUNTRY, cf.USE_PERSIAN_CALENDAR)
    user_events = file_repository.load_events_from_csv()
    user_tasks = file_repository.load_tasks_from_csv()
    holidays = file_repository.load_holidays()
    birthdays = file_repository.load_birthdays_from_abook()
    importer = Importer(user_tasks, user_events, cf.TASKS_FILE, cf.EVENTS_FILE, cf.CALCURSE_TODO_FILE,
                                cf.CALCURSE_EVENTS_FILE, cf.TASKWARRIOR_FOLDER, cf.USE_PERSIAN_CALENDAR)

    # Initialise terminal screen:
    stdscr = curses.initscr()
    curses.noecho()
    curses.curs_set(False)
    initialize_colors()

    # Initialise screen views:
    app_view = View(stdscr, 0, 0)
    monthly_screen_view = MonthlyScreenView(stdscr, 0, 0, weather, user_events, holidays, birthdays, screen)
    daily_screen_view = DailyScreenView(stdscr, 0, 0, weather, user_events, holidays, birthdays, screen)
    journal_screen_view = JournalScreenView(stdscr, 0, 0, weather, user_tasks, screen)
    help_screen_view = HelpScreenView(stdscr, 0, 0, screen)
    footer_view = FooterView(stdscr, 0, 0, screen)
    separator_view = SeparatorView(stdscr, 0, 0, screen)

    # Running different screens depending on the state:
    while screen.state != AppState.EXIT:
        if not screen.split:
            stdscr.clear()
            app_view.fill_background()
        screen.active_pane = False

        # CALENDARS

        # Monthly (active) screen:
        if screen.state == AppState.CALENDAR and screen.calendar_state == CalState.MONTHLY:
            if screen.split and not screen.selection_mode:
                stdscr.clear()
                app_view.fill_background()
                journal_screen_view.render()
            screen.active_pane = True
            monthly_screen_view.render()
            if screen.split: separator_view.render()
            footer_view.render()
            control_monthly_screen(stdscr, user_events, screen, importer)

        # Daily (active) screen:
        elif screen.state == AppState.CALENDAR and screen.calendar_state == CalState.DAILY:
            if screen.split and not screen.selection_mode:
                stdscr.clear()
                app_view.fill_background()
                journal_screen_view.render()
            screen.active_pane = True
            daily_screen_view.render()
            if screen.split: separator_view.render()
            footer_view.render()
            control_daily_screen(stdscr, user_events, screen, importer)

        # JOURNAL

        # Journal (active) screen:
        elif screen.state == AppState.JOURNAL:
            if screen.split and not screen.selection_mode:
                if screen.refresh_now:
                    stdscr.clear()
                    app_view.fill_background()
                if screen.calendar_state == CalState.MONTHLY:
                    monthly_screen_view.render()
                else:
                    daily_screen_view.render()
            screen.active_pane = True
            journal_screen_view.render()
            if screen.split: separator_view.render()
            footer_view.render()
            control_journal_screen(stdscr, user_tasks, screen, importer)

        # Help screen:
        elif screen.state == AppState.HELP:
            help_screen_view.render()
            control_help_screen(stdscr, screen)

        else:
            break

        # If something changed, save the data:
        if user_events.changed:
            file_repository.save_events_to_csv()
            screen.refresh_now = True
        if user_tasks.changed:
            file_repository.save_tasks_to_csv()
            screen.refresh_now = True

    # Cleaning up before quitting:
    curses.echo()
    curses.curs_set(True)
    curses.endwin()


def cli() -> None:
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli()