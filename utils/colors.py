import random as r
import json

def fate():
	return 0x80b0ff

def luck():
	return 0x9eafe3

def random():
	return r.randint(0, 0xFFFFFF)

def theme(ctx):
	with open("./data/userdata/config.json", "r") as f:
		if str(ctx.guild.id) in json.load(f)["color"]:
			return eval(json.load(f)["color"][str(ctx.guild.id)])
	return fate()

def red():
	return 0xff0000

def pink():
	return 0xfc88ff

def orange():
	return 0xff6800

def yellow():
	return 0xffd800

def green():
	return 0x39ff14

def lime_green():
	return 0xb8ff00

def blue():
	return 0x0000FF

def cyan():
	return 0x00ffff

def purple():
	return 0x9400D3

def black():
	return 0x000001

def white():
	return 0xffffff
