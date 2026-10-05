from kurigram.types import InlineKeyboardButton, InlineKeyboardMarkup

def commit_review():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Edit", callback_data="commit:edit"), InlineKeyboardButton("Cancel", callback_data="commit:cancel")], [InlineKeyboardButton("Commit", callback_data="commit:confirm")]])

def repository():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Files", callback_data="repo:files"), InlineKeyboardButton("Commits", callback_data="repo:commits")], [InlineKeyboardButton("Branches", callback_data="repo:branches"), InlineKeyboardButton("Pull requests", callback_data="repo:pulls")], [InlineKeyboardButton("Actions", callback_data="repo:actions")]])

def back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="nav:back")]])
