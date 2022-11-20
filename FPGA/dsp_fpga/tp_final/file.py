from PyQt5.QtWidgets import QFileDialog

def open_file(filter = ...):
	return QFileDialog.getOpenFileName(filter = filter)[0]

def save_file():
	return QFileDialog.getSaveFileName()[0]