from tkinter import messagebox


def show_error(parent, title, message):
    messagebox.showerror(title=title, message=message, parent=parent, icon=messagebox.ERROR)


def show_saved(parent, partner_id, is_editing):
    title = "Изменения сохранены" if is_editing else "Партнёр добавлен"
    action = "Данные партнёра обновлены" if is_editing else "Новый партнёр добавлен"
    messagebox.showinfo(
        title=title, message=f"{action} в базе данных.\nID партнёра: {partner_id}.",
        parent=parent, icon=messagebox.INFO,
    )


def confirm_discard(parent):
    return messagebox.askyesno(
        title="Несохранённые изменения",
        message=("Вы изменили поля карточки. При выходе несохранённые изменения "
                 "будут безвозвратно потеряны.\n\n"
                 "Выйти без сохранения?\n"
                 "«Да» — удалить изменения и выйти. «Нет» — вернуться к форме."),
        parent=parent, icon=messagebox.WARNING, default=messagebox.NO,
    )
