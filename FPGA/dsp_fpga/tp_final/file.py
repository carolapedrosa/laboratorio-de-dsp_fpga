from PyQt5.QtWidgets import QFileDialog

def open_file(filter = ...):
	return QFileDialog.getOpenFileName(filter = filter)[0]

def save_file(filter = ...):
	return QFileDialog.getSaveFileName(filter = filter)[0]