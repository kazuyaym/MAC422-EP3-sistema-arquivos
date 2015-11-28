#!/usr/bin/python

###################################################
#                                                 #
# MAC0422 - Sistemas Operacionais - 2015/02       #
# Caio Lopes Demario                              #
# NUSP 7991187                                    #
# Marcos Kazuya Yamazaki                          #
# NUSP 7577622                                    #
#                                                 #
###################################################

import sys, re, struct, time, datetime

sistemaArquivos = None # false/true, se o sistema de arquivo ja foi montado
disco           = None # a nossa particao do disco simulada

fat = []

BLOCO = 4000        # tamanho de um bloco em byte
TOTAL_BLOCO = 25000 # tamanho total de blocos no disco
ROOT = 15

ACESS = 10
MODIF = 14

# 0: 0000 ..  3999    -> Super bloco (2 bytes para falar o espaco livre)
# 1: 4000 ..  7999    -> FAT
# 2: 8000 .. 11999 
# 3:
# 4:
# .
# .
# .
# 12:
# 13:
# 14: 56000 .. 59999  -> Bitmap
# 15: 60000 .. 63999  -> raiz
# 16: 64000 .. outros arquivos

##################################################################
#
#		Pega a data de agora e transforma em
#       int, para gravar em hex no disco
#
def escreve_data(byte):
	global disco
	
	if byte != -1:
		disco.seek(byte)
	disco.write(struct.pack("i", int(time.time())))

##################################################################
#
#		Le o valor em hex da data no disco e tranforma em datestamp
#       Devolve a string da data!
#
def le_data(byte):
	global disco
	
	disco.seek(byte)
	strData = datetime.datetime.fromtimestamp(struct.unpack("i", disco.read(4))[0]).strftime('%Y-%m-%d %H:%M')
	return strData

#################################################################
#
#
#
def mount(arquivo):
	global disco
	global fat
	global sistemaArquivos
	
	fat = []
	sistemaArquivos = False
	
	try:
		# Abre o arquivo para escritura
		disco = open(arquivo, "r+b")
		
		#####################################
		#   Coloca o FAT na memoria
		#
		disco.seek(1*BLOCO)
		for i in range(0, TOTAL_BLOCO):
			fat.append(struct.unpack("h", disco.read(2))[0])

		sistemaArquivos = True
	except IOError:
		try:                                      #
			disco = open(arquivo, "w+b")          # - Criao arquivo, caso nao arquivo nao existia
												  # Alem de criar, inicialize com espacos vazios
			Binario = bytearray(15*BLOCO)         # - Inicializando com espacos vazios
			disco.write(Binario)                  # equivalente a 15 blocos de 4Kb
			disco.close()                         #
			disco = open(arquivo, "r+b")          # - Abre novamente o arquivo, mas agora
			                                      # para permitir mudancas no arquivo
			#######################################
			#  Superbloco
			#
			disco.seek(0)
			disco.write(struct.pack("i", (TOTAL_BLOCO-15)*BLOCO)) # Escreve o tamanho do espaco livre no superbloco
			
			####################################
			#  Escreve o FAT
			# 
			disco.seek(1*BLOCO)
			for i in range(0, TOTAL_BLOCO):
				disco.write(struct.pack("h", -1))
				
			fat = [-1]*TOTAL_BLOCO
			
			#####################################
			#  Criando o BitMap
			# 
			disco.seek(14*BLOCO)
			array = [0,1]
			for i in range(3, TOTAL_BLOCO/8):
				array.append(255)
			array.append(254) # ultimo bloco, aqui estamos representanco o super
			                  # bloco, que esta ocupado, pois ele eh o bloco 0
			binario = bytearray(array)
			disco.write(binario)
			
			#####################################
			#  Criando o diretorio Root
			# 
			disco.seek(15*BLOCO)
			Binario = bytearray(BLOCO)     # Escreve o tamanho em byte da entrada raiz
			disco.write(Binario)
			
			disco.seek(15*BLOCO)
			disco.write(struct.pack("h", 21))    # Escreve o tamanho em byte da entrada raiz
			disco.write(struct.pack("i", -1))
			escreve_data(-1)                     # Escreve data de criacao
			escreve_data(-1)                     # Escreve data de acesso
			escreve_data(-1)                     # Escreve data de modificacao
			disco.write(struct.pack("h", 15))    # 2 fat

			sistemaArquivos = True
		except IOError:
			print "Nao foi possivel criar e/ou abrir o arquivo " + arquivo
			sistemaArquivos = False
	return


##################################################################
#
#		Acha o proximo bloco livre para comecar a escrever nela
#		Como no disco pegamos byte a byte, verificamos se esse byte
#       nao vale FF, pois caso sim, ela todos os bits (blocos) nesse
#       'bloquinho' estao ocupados, e vamos ao proximo ate encontrar
#		 
#		Depois de encontrar, transformamos o numero em binario
#		para achar o local exato do bloco livre, para transformamos
#		em hex para gravar no disco
#
#		Funcao devolve o bloco livre!
#
def procura_bloco_livre():
	bit = 0
	disco.seek(BLOCO*14)
	
	# Le byte a byte 
	valor = ord(struct.unpack("c", disco.read(1))[0])
	
	while valor == 0:
		bit += 8
		
		if bit == TOTAL_BLOCO:
			print "O seu disco esta cheio!"
			return -1
			
		valor = ord(struct.unpack("c", disco.read(1))[0])
	
	index = find_index(valor)
	set_bit(valor, index, 0, bit/8)
		
	return (8 - index) + bit

# 	1000 0000 -> entre [128, 256) trocar bit 7
# 	01?? ???? -> entre [64 , 128) trocar bit 6
# 	001? ???? -> entre [32 , 64)  trocar bit 5
# 	0001 ???? -> entre [16 , 32)  trocar bit 4
# 	0000 1??? -> entre [8  , 16)  trocar bit 3
# 	0000 01?? -> entre [4  , 8)   trocar bit 2
# 	0000 001? -> entre [2  , 4)   trocar bit 1
# 	0000 0001 -> entre [1  , 2)   trocar bit 0
# 	0000 0000 -> ocupado, Proximo byte

def set_bit(valor, index, x, byte):
	binario = 1 << index # Left-Shift, para trocar o bit 'index' 
	
	valor &= ~binario # inverte todos os bits de binario, e faz um (valor && ~binario) bit a bit
	if x:
		valor |= binario # Faz um (valor || binario) bit a bit
	
	disco.seek(BLOCO*14 + byte)
	disco.write(struct.pack("c", chr(valor)))
	
	return valor

def find_index(num):
	if   num >= 128: return 7
	elif num >=  64: return 6
	elif num >=  32: return 5
	elif num >=  16: return 4
	elif num >=   8: return 3
	elif num >=   4: return 2
	elif num >=   2: return 1
	else:            return 0

#################################################################
#
#	Busca o bloco em que a ultima pasta do array 'pastas' esta
#
def busca_diretorio(pastas, cmd_ls):
	global disco

	bloco = ROOT
	
	if cmd_ls == 0:
		escreve_data((ROOT*BLOCO)+ACESS)	
	
	if len(pastas) == 0:
		return bloco, bloco	, 0	
		
	for pasta in pastas:
		blocoPai = bloco
		bloco, pos = busca_arquivo(bloco, pasta, True, cmd_ls)
		
		if bloco == 0: return 0,0,0 # nao foi encontrado
	
	return bloco, blocoPai, pos

#################################################################
#
#   Busca por arquivo ou diretorio 'nome', no bloco dado, que eh um diretorio
#   RETORNA O BLOCO QUE ESTE ARQUIVO ESTA, FAT!!!! NAO O BLOCO PAI DELE
#
def busca_arquivo(bloco, nome, procuroDir, cmd_ls):
	global disco
	# print "busca_arquivo: nome: " + nome

	while True:
		pos = 0
		disco.seek(bloco*BLOCO)
		tamanhoMetadado = struct.unpack("h", disco.read(2))[0]

		# print "busca_arquivo: tamanhoMetadado: " + str(tamanhoMetadado)
		
		while tamanhoMetadado != 0:
			# TODO: verifica o tamanho, se for != -1, ele nao eh [dir]
			disco.seek((bloco*BLOCO)+pos+2)
			tamanho = struct.unpack("i", disco.read(4))[0]
			
			if (procuroDir and tamanho == -1) or ((not procuroDir) and tamanho != -1):
			
				disco.seek((bloco*BLOCO)+pos+20)
				char = struct.unpack("c", disco.read(1))[0]
				i = 0
	
				while i < len(nome) and nome[i] == char and char != '\0':
					# print "busca_arquivo: nome[" + str(i) + "]: " + nome[i]
					# print "busca_arquivo: char: " + char
					char = struct.unpack("c", disco.read(1))[0]
					i += 1
				if i == len(nome) and char == '\0': # le o atributo fat desse metadado
					disco.seek((bloco*BLOCO)+pos+18)
					k = struct.unpack("h", disco.read(2))[0]
					
					if cmd_ls == 0:
						#Atualiza a data de ultimo acesso do diretorio
						escreve_data((bloco*BLOCO)+pos+ACESS)
						
					# print "busca_arquivo: return: " + str(k)
					return k, pos
			
			pos += tamanhoMetadado
			disco.seek(bloco*BLOCO + pos)
			tamanhoMetadado = struct.unpack("h", disco.read(2))[0]

		if fat[bloco] == -1:      # chegou ao final do bloco sem encontrar, 
			break                 # verifica se ha outro bloco com a continuacao 
		else:                     # dos arquivos e continua procurando, ou
			bloco = fat[bloco]    # termina se nao tiver
	
	return 0, 0 # nao foi encontrado

#################################################################
#
#   Ve se o bloco possui espaco suficiente, para colocar
#   a entrada (metadados) do arquivo/diretorio
#
def verifica_espaco_livre(blocoPai, espaco):
	# print "verifica_espaco_livre: blocoPai: " + str(blocoPai)
	global disco
	global fat
	
	while True:
		disco.seek(blocoPai*BLOCO)
		iterador = struct.unpack("h", disco.read(2))[0]
		
		pos = iterador
		
		while iterador != 0:
			
			# print "verifica_espaco_livre: blocoPai: " + str(blocoPai)
			# print "verifica_espaco_livre: pos: " + str(pos)
			# print "verifica_espaco_livre: soma: " + str(blocoPai*BLOCO + pos)

			disco.seek(blocoPai*BLOCO + pos)
			iterador = struct.unpack("h", disco.read(2))[0]
			pos += iterador
		
		if BLOCO-pos < espaco:
			if fat[blocoPai] != -1:
				blocoPai = fat[blocoPai]
			else:
				fat[blocoPai] = procura_bloco_livre()
				blocoPai = fat[blocoPai]
				# TODO: gravar no disco!
		else:
			break
		
	return blocoPai, pos

#################################################################
#
#
#
def gravar_metadado(nome, pai, primeiroBloco, tamTotal):
	global disco
	
	tamMeta = 20 + len(nome) + 1
	pai, posicao = verifica_espaco_livre(pai, tamMeta)

	# print "gravar_metadado: tamMeta: " + str(tamMeta)

	disco.seek((pai*BLOCO)+posicao)

	disco.write(struct.pack("h", tamMeta)) 		 # [ 0]  2 tamanho da entrada
	disco.write(struct.pack("i", tamTotal))      # [ 2]  4 tamanho do arquivo
	escreve_data(-1)             		         # [ 6]  4 dataCriacao    
	escreve_data(-1)             		         # [10]  4 dataAcesso
	escreve_data(-1)            		         # [14]  4 dataModificado
	disco.write(struct.pack("h", primeiroBloco)) # [18]  2 fat
	disco.write(bytearray(nome))           		 # [20]  nome

	disco.seek((pai*BLOCO)+posicao)
	valor = struct.unpack("h", disco.read(2))[0]
	
	return True

#################################################################
#
#
#
def inicializar_bloco(blocoLivre):
	global disco

	disco.seek(blocoLivre*BLOCO)
	Binario = bytearray(BLOCO)
	disco.write(Binario)
	
	return True

#################################################################
#
#		Dados que serao gravados num diretorio
#
#		Tamanho dessa entrada : 2 bytes
#		Tamanho em bytes      : 4 bytes (valor -1 no caso de diretorio)
#		dataCriacao           : 4 bytes
#		dataModificado        : 4 bytes
#		dataAcesso            : 4 bytes
#		fat                   : 2 bytes
#		Nome                  : ? bytes (max de 255 bytes)
#       ----------------------+--------
#                              (20 + Nome) bytes
#


def mkdir(diretorio):
	global disco
	
	tmp = re.match(r'/*([a-z0-9-_/]+[^/])/*$', diretorio)
	pastas = tmp.group(1).split('/')
	
	nome = pastas.pop(-1)                      # Retira o ultimo elemento que seria o nome da pasta que queremos criar
	
	if len(nome) > 255:
		print "O nome do arquivo possui mais que 255 caracteres!"
		return

	
	blocoPai, blocoAvo, pos   = busca_diretorio(pastas, 0)    # Acha o bloco onde sera gravado os metadados (se houver espaco)
	if blocoPai == 0: 
		print "Este diretorio nao existe"
		return

	if busca_arquivo (blocoPai, nome, True, 0)[0] != 0:
		print "Este diretorio ja existe"
		return

	blocoLivre = procura_bloco_livre()         # Acha o bloco onde sera gravado os arquivos desse diretorio
	# print "Inserindo pasta: " + nome
	# print "No bloco livre " + str(blocoLivre)
	# print "Com metadados em " + str(blocoPai)  # DEBUG
	
	gravar_metadado(nome, blocoPai, blocoLivre, -1)
	inicializar_bloco(blocoLivre)
	
	escreve_data((blocoAvo*BLOCO)+pos+MODIF)     # Atualiza o instante de modificacao do diretorio

	return

#################################################################
#
#	Copia um arquivo do sistema real para o nosso sistema
#	simulado, esses arquivos copiados serao todos em text
#	puro. Onde o argumento 'origem' eh o caminho desde o
#	root ate o arquivo, e destino tambem eh o caminho a 
#	partir do root do sistema simulado
#
def cp(origem, destino):
	global disco

	arqOrigem = open(origem, "r+b")

	i = 0
	tamanhoArq = 1
	blocoPai, blocoDestino = touch(destino)
	if blocoPai == 0:
		return

	disco.seek(blocoDestino*BLOCO)

	ch = arqOrigem.read(1)
	while ch :
		tamanhoArq += 1
		disco.write(ch)
		i += 1

		if i >= BLOCO:
			i = 0
			fat[blocoDestino] = procura_bloco_livre()
			blocoDestino = fat[blocoDestino]
			disco.seek(blocoDestino*BLOCO)
			# TODO: gravar no disco
		ch = arqOrigem.read(1)

	tmp = re.match(r'/*([a-z0-9-_/]+[^/])/*$', destino)
	nome = tmp.group(1).split('/').pop(-1)
	
	pos = busca_arquivo(blocoPai, nome, False, 0)[1]
	#TODO: quando o dir ocupa mais de um bloco
	
	disco.seek(blocoPai*BLOCO + pos + 2)
	disco.write(struct.pack("i", tamanhoArq))
	
	return

#################################################################
#
#
#
def cat(arquivo):
	i = 0
	tmp = re.match(r'/*([a-z0-9-_/]+[^/])/*$', arquivo)
	pastas = tmp.group(1).split('/')
	nome = pastas.pop(-1)
	
	bloco, blocoPai, pos = busca_diretorio(pastas, 0)
	blocoArq = busca_arquivo(bloco, nome, False,  0)[0]
	
	disco.seek(blocoArq*BLOCO)
	# ch = ord(struct.unpack("c", disco.read(1))[0])
	ch = disco.read(1)
	while ch and ord(struct.unpack("c", ch)[0]) != 0:
		sys.stdout.write(ch)
		i += 1
		if i >= BLOCO:
			blocoArq = fat[blocoArq]
			disco.seek(blocoArq*BLOCO)
			i = 0
		ch = disco.read(1)
		# ch = ord(struct.unpack("c", disco.read(1))[0])
	return	

#################################################################
#
#
#
def touch(arquivo):
	global disco

	if re.search('^/$' , arquivo):
		print "Especifique o nome do arquivo"
		return 0, 0
	
	tmp = re.match(r'/*([a-z0-9-_/]+[^/])/*$', arquivo)
	pastas = tmp.group(1).split('/')
	
	nome = pastas.pop(-1)                      # Retira o ultimoe lemento que seria o nome da pasta que queremos criar

	if len(nome) > 255:
		print "O nome do arquivo possui mais que 255 caracteres!"
		return 0 ,0

	blocoPai, blocoAvo, pos  = busca_diretorio(pastas, 0)    # Acha o bloco onde sera gravado os metadados (se houver espaco)
	
	if busca_arquivo(blocoPai, nome, False, 0)[0] != 0:
		#escreve_data((blocoPai*BLOCO) + pos2 + ACESS)
		return
	
	blocoLivre = procura_bloco_livre()         # Acha o bloco onde sera gravado os arquivos desse diretorio
	
	# print "Inserindo pasta: " + nome
	# print "No bloco livre " + str(blocoLivre)
	# print "Com metadados em " + str(blocoPai)  # DEBUG
	
	gravar_metadado(nome, blocoPai, blocoLivre, 0)
	inicializar_bloco(blocoLivre)
	
	escreve_data((blocoAvo*BLOCO)+pos+MODIF)     # Atualiza o instante de modificacao do arquivo

	return blocoPai, blocoLivre

#################################################################
#
#
#
def rm(arquivo):
	tmp = re.match(r'/*([a-z0-9-_/]+[^/])/*$', arquivo)
	pastas = tmp.group(1).split('/')
	
	nome = pastas.pop(-1)
	blocoPai, blocoAvo, pos = busca_diretorio(pastas, 0)
	blocoArq, pos2 = busca_arquivo(blocoPai, nome, False, 0)
	
	while True:
		inicializar_bloco(blocoArq)
		if fat[blocoArq] == -1:
			break
		aux = fat[blocoArq]
		blocoArq = aux
		fat[blocoArq] = -1
	
	disco.seek(blocoPai*BLOCO + pos2)
	offset = struct.unpack("h", disco.read(2))[0]
	i = 0
	while True:
		disco.seek(blocoPai*BLOCO + pos2 + offset + i)
		ch = struct.unpack("c", disco.read(1))[0]
		disco.seek(blocoPai*BLOCO + pos2 + i)
		disco.write(struct.pack("c", ch))
		i+=1
		if pos2 + offset + i >= BLOCO:
			break
		

	return

################################################################################
#
#																			  LS
#
#
def ls(diretorio):
	global disco
	
	pastas = []
	
	if not re.search('^/$' , diretorio):
		tmp = re.match(r'/*([a-z0-9-_/]+[^/])/*$', diretorio)
		pastas = tmp.group(1).split('/')

	# print "ls: pastas: " + str(pastas)
	blocoDiretorio = busca_diretorio(pastas, 1)[0]

	if blocoDiretorio == 0:
		print "Este diretorio nao existe"
		return
	# print "ls: blocoDiretorio: " + str(blocoDiretorio)
	lista_arquivos(blocoDiretorio)
	
	return

#
#
#   Busca por arquivo ou diretorio 'nome', 
#   no bloco dado, que eh um diretorio
#
#
def lista_arquivos (bloco):
	global disco
	
	pos = 0

	while True:
		disco.seek(bloco*BLOCO)
		tamanhoMetadado = struct.unpack("h", disco.read(2))[0]

		while tamanhoMetadado != 0:
			disco.seek((bloco*BLOCO)+pos+20)

			nome = ""
			char = struct.unpack("c", disco.read(1))[0]
			while char != '\0':
				# print "lista_arquivos: char: " + char
				nome += char
				char = struct.unpack("c", disco.read(1))[0]
			
			disco.seek(bloco*BLOCO +pos + 2)
			tamanho = struct.unpack("i", disco.read(4))[0]
			if tamanho == -1:
				tamanho = "[dir]"
				nome += "/"

			modif = le_data(BLOCO*bloco + pos + MODIF)
			# print "lista_arquivos: nome: " + nome
			# print "lista_arquivos: tamanho: "+ str(tamanho)
			# print "lista_arquivos: modif "+ le_data(BLOCO*bloco + pos + MODIF)

			if nome != "/":
				print modif + " " + str(tamanho).rjust(9) + " " + nome

			pos += tamanhoMetadado
			disco.seek(bloco*BLOCO + pos)
			tamanhoMetadado = struct.unpack("h", disco.read(2))[0]
		if fat[bloco] == -1:
			break    
		else: 
			bloco = fat[bloco]
	
	return


#################################################################

def busca_arquivo_find(pastas, bloco, nome):
	global disco
	# print "busca_arquivo: nome: " + nome
	if len(pastas) == 0:
		pastas = []

	while True:
		pos = 0
		disco.seek(bloco*BLOCO)
		tamanhoMetadado = struct.unpack("h", disco.read(2))[0]

		# print "busca_arquivo: tamanhoMetadado: " + str(tamanhoMetadado)
		
		while tamanhoMetadado != 0:
			disco.seek((bloco*BLOCO)+pos+2)
			tamanho = struct.unpack("i", disco.read(4))[0]
			
			
			
			disco.seek((bloco*BLOCO)+pos+20)
			char = struct.unpack("c", disco.read(1))[0]

			string = ""
			while char != '\0':  
				string += char
				char = struct.unpack("c", disco.read(1))[0]

			i = 0
			while i < len(nome) and i < len(string) and nome[i] == string[i]:
				i += 1

			if tamanho != -1:	
				if i == len(nome) and i == len(string): # le o atributo fat desse metadado
					disco.seek((bloco*BLOCO)+pos+18)
					k = struct.unpack("h", disco.read(2))[0]
					
					escreve_data((bloco*BLOCO)+pos+ACESS)
						
					# print "busca_arquivo: return: " + str(k)
					print '/'.join(pastas) + "/" + nome
			else: 
				# RECURSAO FAT
				pastas.append([string])
				k = struct.unpack("h", disco.read(2))[0]
				print string
				print pastas
				print k
				pastas = busca_arquivo_find(pastas, k, nome)
			
			pos += tamanhoMetadado
			disco.seek(bloco*BLOCO + pos)
			tamanhoMetadado = struct.unpack("h", disco.read(2))[0]

		if fat[bloco] == -1: break 
		else: bloco = fat[bloco]

	if len(pastas) != 0: 
		return pastas.pop()
	else: return pastas 

#################################################################
#
#																			
#
def find(diretorio, arquivo):
	pastas = []
	if re.search('^/$' , diretorio):
		busca_arquivo_find(pastas, ROOT, arquivo)
	else:
		tmp = re.match(r'/*([a-z0-9-_/]+[^/])/*$', diretorio)
		pastas = tmp.group(1).split('/')
		busca_arquivo_find(pastas, busca_diretorio(pastas, 1)[0], arquivo)
	return

#################################################################
#
#
#
def df():
	return

#################################################################
#
#
#
def umount():
	global disco
	global sistemaArquivos

	sistemaArquivos = False
	disco.close()
	return
	
	
#################################################################
#
#     MAIN
#
while 1:
	sys.stdout.write("[ep3]: ")
	line = sys.stdin.readline()
	line = re.sub(r'\n$', '', line)
	line = re.sub(r'\s$', '', line)

	if re.search('^mount /[a-z0-9.-_/]+' , line):
		line = re.sub(r'mount ', '', line)
		arquivoDisco = line
		mount(arquivoDisco)
	
	elif re.search('^sai$' , line):
		if sistemaArquivos:
			umount()
		break

	else:
		if sistemaArquivos:
			if re.search('^cp /*[a-z0-9.-_/]+ [a-z0-9.-_/]+' , line):
				if not re.search('^cp /[^ ]+ /', line):
					print "Especifique o nome do arquivo ou diretorio com o caminho completo a partir da raiz '/'"
				else:
					tmp = re.match(r'^cp ([a-z0-9.-_/]+) ([a-z0-9.-_/]+)', line)
					cp(tmp.group(1), tmp.group(2))

			elif re.search('^mkdir [a-z0-9.-_/]+' , line):
				line = re.sub(r'mkdir ', '', line)
				diretorio = line
				mkdir(diretorio)
			
			elif re.search('^rmdir [a-z0-9.-_/]+' , line):
				line = re.sub(r'rmdir ', '', line)
				diretorio = line
				rmdir(diretorio)
			
			elif re.search('^cat [a-z0-9.-_/]+' , line):
				line = re.sub(r'cat ', '', line)
				arquivo = line
				cat(arquivo)
			
			elif re.search('^touch [a-z0-9.-_/]+' , line):
				line = re.sub(r'touch ', '', line)
				arquivo = line
				touch(arquivo)
			
			elif re.search('^rm [a-z0-9.-_/]+' , line):
				line = re.sub(r'rm ', '', line)
				arquivo = line
				rm(arquivo)
			
			elif re.search('^ls [a-z0-9.-_/]+' , line):
				line = re.sub(r'ls ', '', line)
				diretorio = line
				ls(diretorio)

			elif re.search('^ls\s*$' , line):
				ls("/")
		
			elif re.search('^find [a-z0-9.-_/]+ [a-z0-9.-_/]+' , line):
				tmp = re.match(r'^find ([a-z0-9.-_/]+) ([a-z0-9.-_/]+)', line)
				find(tmp.group(1), tmp.group(2))
			
			elif re.search('^df$' , line):
				df()
			
			elif re.search('^umount$' , line):
				umount()
			else:
				print "Comando nao reconhecido!"
		
		else: 
			print "Monte seu arquivo antes de executar algum comando!"

####################################################################################################	