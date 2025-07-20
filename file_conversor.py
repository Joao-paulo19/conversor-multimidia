import os
import sys
import re
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
import logging
from pathlib import Path
import time
from datetime import datetime


class FileConverter:
    def __init__(self, root):
        # Configuração principal da janela
        self.root = root
        self.root.title("Conversor de Arquivos Multimídia")
        self.root.geometry("700x650")
        self.root.configure(bg="#f0f0f0")
        self.root.resizable(True, True)

        # Variáveis
        self.arquivo_origem_var = tk.StringVar()
        self.pasta_destino_var = tk.StringVar()
        self.formato_destino_var = tk.StringVar()
        self.qualidade_var = tk.StringVar()
        self.modo_conversao_var = tk.StringVar(value="audio")

        self.processo_ativo = None
        self.cancelar_conversao = False

        # Extensões suportadas por categoria
        self.extensoes_audio = {
            'mp3': 'MPEG Layer III',
            'wav': 'Waveform Audio',
            'flac': 'Free Lossless Audio',
            'aac': 'Advanced Audio Codec',
            'ogg': 'Ogg Vorbis',
            'm4a': 'MPEG-4 Audio',
            'opus': 'Opus',
            'alac': 'Apple Lossless Audio',
            'aiff': 'Audio Interchange',
            'amr': 'Adaptive Multi-Rate'
        }

        self.extensoes_video = {
            'mp4': 'MPEG-4 Part 14',
            'mkv': 'Matroska Video',
            'avi': 'Audio Video Interleave',
            'mov': 'QuickTime Movie',
            'webm': 'Web Media',
            'flv': 'Flash Video',
            'wmv': 'Windows Media Video',
            '3gp': '3GPP Media File',
            'ts': 'Transport Stream',
            'm4v': 'MPEG-4 Video'
        }

        self.extensoes_imagem = {
            'jpg': 'JPEG Image',
            'jpeg': 'JPEG Image',
            'png': 'Portable Network Graphics',
            'bmp': 'Bitmap Image',
            'tiff': 'TIFF Image',
            'tif': 'TIFF Image',
            'heic': 'HEIC Image',
            'ico': 'Icon File',
            'webp': 'WebP Image',
            'svg': 'Scalable Vector Graphics'
        }

        self.extensoes_gif = {
            'gif': 'Graphics Interchange Format',
            'webp': 'WebP Animado',
            'apng': 'Animated PNG'
        }

        # Qualidades disponíveis
        self.qualidades_audio = [
            "Manter Original",
            "320kbps (Alta)",
            "256kbps (Alta)",
            "192kbps (Média)",
            "128kbps (Padrão)",
            "96kbps (Baixa)",
            "64kbps (Muito Baixa)"
        ]

        self.qualidades_video = [
            "Manter Original",
            "4K (2160p)",
            "1080p (Full HD)",
            "720p (HD)",
            "480p (SD)",
            "360p (SD Baixa)"
        ]

        # Inicializar valores padrão
        self.qualidade_var.set(self.qualidades_audio[0])

        # Verificar dependências
        if not self.verificar_dependencias():
            messagebox.showerror(
                "Erro", "FFmpeg não encontrado. Por favor, instale o FFmpeg para usar este conversor.")
            return

        # Criar a interface
        self.criar_interface()

    def recurso_caminho(self, relativo):
        """Detecta o caminho de recursos"""
        try:
            if hasattr(sys, '_MEIPASS'):
                caminho = os.path.join(sys._MEIPASS, relativo)
            else:
                caminho = os.path.join(os.path.abspath("."), relativo)

            if os.path.exists(caminho):
                return caminho
            else:
                import shutil
                return shutil.which(relativo.replace('.exe', ''))
        except Exception as e:
            return None

    def verificar_dependencias(self):
        """Verifica se o FFmpeg está disponível"""
        try:
            ffmpeg_path = self.recurso_caminho(
                "ffmpeg.exe") or self.recurso_caminho("ffmpeg")
            if ffmpeg_path:
                return True

            # Tentar encontrar no PATH do sistema
            import shutil
            return shutil.which("ffmpeg") is not None
        except Exception as e:
            return False

    def obter_ffmpeg_path(self):
        """Obtém o caminho do FFmpeg"""
        ffmpeg_path = self.recurso_caminho(
            "ffmpeg.exe") or self.recurso_caminho("ffmpeg")
        if ffmpeg_path:
            return ffmpeg_path

        import shutil
        return shutil.which("ffmpeg")

    def detectar_tipo_arquivo(self, arquivo):
        """Detecta o tipo do arquivo baseado na extensão"""
        if not arquivo:
            return "desconhecido"

        extensao = arquivo.lower().split('.')[-1]

        if extensao in self.extensoes_audio:
            return "audio"
        elif extensao in self.extensoes_video:
            return "video"
        elif extensao in self.extensoes_imagem:
            return "imagem"
        elif extensao in self.extensoes_gif:
            return "gif"
        else:
            return "desconhecido"

    def criar_interface(self):
        """Cria a interface gráfica do aplicativo"""
        try:
            # Estilo para widgets
            estilo = ttk.Style()
            estilo.configure("TButton", font=("Segoe UI", 10))
            estilo.configure("TLabel", font=(
                "Segoe UI", 10), background="#f0f0f0")
            estilo.configure("Header.TLabel", font=(
                "Segoe UI", 12, "bold"), background="#f0f0f0")
            estilo.configure("TFrame", background="#f0f0f0")
            estilo.configure("TRadiobutton", background="#f0f0f0")

            # Frame principal
            main_frame = ttk.Frame(self.root, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Título
            titulo_label = ttk.Label(main_frame, text="Conversor de Arquivos Multimídia",
                                     style="Header.TLabel", font=("Segoe UI", 16, "bold"))
            titulo_label.pack(pady=(0, 20))

            # Frame para arquivo de origem
            origem_frame = ttk.Frame(main_frame)
            origem_frame.pack(fill=tk.X, pady=5)

            ttk.Label(origem_frame, text="Arquivo de origem:").pack(
                side=tk.LEFT, padx=(0, 10))
            self.entry_origem = ttk.Entry(
                origem_frame, textvariable=self.arquivo_origem_var, width=40)
            self.entry_origem.pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Button(origem_frame, text="Procurar...", command=self.escolher_arquivo).pack(
                side=tk.LEFT, padx=(10, 0))

            # Frame para tipo detectado
            self.tipo_frame = ttk.Frame(main_frame)
            self.tipo_frame.pack(fill=tk.X, pady=5)
            self.tipo_label = ttk.Label(
                self.tipo_frame, text="Selecione um arquivo para detectar o tipo")
            self.tipo_label.pack(side=tk.LEFT)

            # Notebook para abas de conversão
            self.notebook = ttk.Notebook(main_frame)
            self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)

            # Criar abas
            self.aba_audio = ttk.Frame(self.notebook, padding=10)
            self.aba_video = ttk.Frame(self.notebook, padding=10)
            self.aba_imagem = ttk.Frame(self.notebook, padding=10)

            self.configurar_aba_audio()
            self.configurar_aba_video()
            self.configurar_aba_imagem()

            # Frame para pasta de destino
            pasta_frame = ttk.Frame(main_frame)
            pasta_frame.pack(fill=tk.X, pady=10)

            ttk.Label(pasta_frame, text="Pasta de destino:").pack(
                side=tk.LEFT, padx=(0, 10))
            ttk.Entry(pasta_frame, textvariable=self.pasta_destino_var,
                      width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Button(pasta_frame, text="Escolher...", command=self.escolher_pasta).pack(
                side=tk.LEFT, padx=(10, 0))

            # Barra de progresso
            progresso_frame = ttk.Frame(main_frame)
            progresso_frame.pack(fill=tk.X, pady=10)

            self.progresso_label = ttk.Label(
                progresso_frame, text="Selecione um arquivo para começar")
            self.progresso_label.pack(fill=tk.X)

            self.barra_progresso = ttk.Progressbar(
                progresso_frame, orient=tk.HORIZONTAL, length=100, mode='indeterminate')
            self.barra_progresso.pack(fill=tk.X, pady=5)

            # Botões
            botao_frame = ttk.Frame(main_frame)
            botao_frame.pack(fill=tk.X, pady=10)

            self.botao_cancelar = ttk.Button(
                botao_frame, text="Cancelar", command=self.cancelar_operacao, width=20, state=tk.DISABLED)
            self.botao_cancelar.pack(side=tk.RIGHT, padx=(10, 0))

            self.botao_converter = ttk.Button(
                botao_frame, text="Converter", command=self.iniciar_conversao, width=20)
            self.botao_converter.pack(side=tk.RIGHT)

            # Bind para detectar mudanças no arquivo
            self.arquivo_origem_var.trace('w', self.on_arquivo_mudou)

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao criar interface: {e}")

    def configurar_aba_audio(self):
        """Configura os widgets da aba de áudio"""
        try:
            # Formato de saída
            formato_frame = ttk.Frame(self.aba_audio)
            formato_frame.pack(fill=tk.X, pady=10)

            ttk.Label(formato_frame, text="Converter para:").pack(
                side=tk.LEFT, padx=(0, 10))
            formatos_audio = list(self.extensoes_audio.keys())
            self.combo_formato_audio = ttk.Combobox(formato_frame, textvariable=self.formato_destino_var,
                                                    values=formatos_audio, width=15, state="readonly")
            self.combo_formato_audio.pack(side=tk.LEFT)
            self.combo_formato_audio.set('mp3')

            # Qualidade
            qualidade_frame = ttk.Frame(self.aba_audio)
            qualidade_frame.pack(fill=tk.X, pady=10)

            ttk.Label(qualidade_frame, text="Qualidade:").pack(
                side=tk.LEFT, padx=(0, 10))
            self.combo_qualidade_audio = ttk.Combobox(qualidade_frame, textvariable=self.qualidade_var,
                                                      values=self.qualidades_audio, width=20, state="readonly")
            self.combo_qualidade_audio.pack(side=tk.LEFT)
            self.combo_qualidade_audio.set(self.qualidades_audio[0])

            # Informações
            info_frame = ttk.Frame(self.aba_audio)
            info_frame.pack(fill=tk.X, pady=10)

            info_text = ("Converte arquivos de áudio entre diferentes formatos.\n"
                         f"Formatos suportados: {', '.join(list(self.extensoes_audio.keys())[:5])}...")

            ttk.Label(info_frame, text=info_text, wraplength=500,
                      justify=tk.LEFT).pack(fill=tk.X)

        except Exception as e:
            messagebox.showerror(
                "Erro", f"Erro ao configurar aba de áudio: {e}")

    def configurar_aba_video(self):
        """Configura os widgets da aba de vídeo"""
        try:
            # Formato de saída
            formato_frame = ttk.Frame(self.aba_video)
            formato_frame.pack(fill=tk.X, pady=10)

            ttk.Label(formato_frame, text="Converter para:").pack(
                side=tk.LEFT, padx=(0, 10))
            formatos_video = list(self.extensoes_video.keys())
            self.combo_formato_video = ttk.Combobox(formato_frame, textvariable=self.formato_destino_var,
                                                    values=formatos_video, width=15, state="readonly")
            self.combo_formato_video.pack(side=tk.LEFT)
            self.combo_formato_video.set('mp4')

            # Qualidade
            qualidade_frame = ttk.Frame(self.aba_video)
            qualidade_frame.pack(fill=tk.X, pady=10)

            ttk.Label(qualidade_frame, text="Resolução:").pack(
                side=tk.LEFT, padx=(0, 10))
            self.combo_qualidade_video = ttk.Combobox(qualidade_frame, textvariable=self.qualidade_var,
                                                      values=self.qualidades_video, width=20, state="readonly")
            self.combo_qualidade_video.pack(side=tk.LEFT)
            self.combo_qualidade_video.set(self.qualidades_video[0])

            # Informações
            info_frame = ttk.Frame(self.aba_video)
            info_frame.pack(fill=tk.X, pady=10)

            info_text = ("Converte arquivos de vídeo entre diferentes formatos.\n"
                         f"Formatos suportados: {', '.join(list(self.extensoes_video.keys())[:5])}...")

            ttk.Label(info_frame, text=info_text, wraplength=500,
                      justify=tk.LEFT).pack(fill=tk.X)

        except Exception as e:
            messagebox.showerror(
                "Erro", f"Erro ao configurar aba de vídeo: {e}")

    def configurar_aba_imagem(self):
        """Configura os widgets da aba de imagem"""
        try:
            # Formato de saída
            formato_frame = ttk.Frame(self.aba_imagem)
            formato_frame.pack(fill=tk.X, pady=10)

            ttk.Label(formato_frame, text="Converter para:").pack(
                side=tk.LEFT, padx=(0, 10))
            # Combinar imagens estáticas e animadas
            formatos_imagem = list(
                self.extensoes_imagem.keys()) + list(self.extensoes_gif.keys())
            formatos_imagem = list(set(formatos_imagem))  # Remover duplicatas
            self.combo_formato_imagem = ttk.Combobox(formato_frame, textvariable=self.formato_destino_var,
                                                     values=formatos_imagem, width=15, state="readonly")
            self.combo_formato_imagem.pack(side=tk.LEFT)
            self.combo_formato_imagem.set('jpg')

            # Qualidade (só para JPEG)
            qualidade_frame = ttk.Frame(self.aba_imagem)
            qualidade_frame.pack(fill=tk.X, pady=10)

            ttk.Label(qualidade_frame, text="Qualidade JPEG:").pack(
                side=tk.LEFT, padx=(0, 10))
            qualidades_jpeg = [
                "Máxima (100%)", "Alta (90%)", "Boa (75%)", "Média (60%)", "Baixa (40%)"]
            self.combo_qualidade_imagem = ttk.Combobox(qualidade_frame, textvariable=self.qualidade_var,
                                                       values=qualidades_jpeg, width=20, state="readonly")
            self.combo_qualidade_imagem.pack(side=tk.LEFT)
            self.combo_qualidade_imagem.set(qualidades_jpeg[1])

            # Informações
            info_frame = ttk.Frame(self.aba_imagem)
            info_frame.pack(fill=tk.X, pady=10)

            info_text = ("Converte imagens entre diferentes formatos.\n"
                         f"Suporta: {', '.join(list(self.extensoes_imagem.keys())[:4])}, GIF, WebP animado...")

            ttk.Label(info_frame, text=info_text, wraplength=500,
                      justify=tk.LEFT).pack(fill=tk.X)

        except Exception as e:
            messagebox.showerror(
                "Erro", f"Erro ao configurar aba de imagem: {e}")

    def on_arquivo_mudou(self, *args):
        """Chamado quando o arquivo de origem muda"""
        try:
            arquivo = self.arquivo_origem_var.get()
            if arquivo and os.path.isfile(arquivo):
                tipo = self.detectar_tipo_arquivo(arquivo)
                extensao = arquivo.lower().split('.')[-1]

                # Atualizar label do tipo
                if tipo == "audio":
                    descricao = self.extensoes_audio.get(extensao, "Áudio")
                    self.tipo_label.config(
                        text=f"Tipo detectado: Áudio ({extensao.upper()}) - {descricao}")
                    self.selecionar_aba_audio()
                elif tipo == "video":
                    descricao = self.extensoes_video.get(extensao, "Vídeo")
                    self.tipo_label.config(
                        text=f"Tipo detectado: Vídeo ({extensao.upper()}) - {descricao}")
                    self.selecionar_aba_video()
                elif tipo in ["imagem", "gif"]:
                    descricoes = {**self.extensoes_imagem,
                                  **self.extensoes_gif}
                    descricao = descricoes.get(extensao, "Imagem")
                    self.tipo_label.config(
                        text=f"Tipo detectado: Imagem ({extensao.upper()}) - {descricao}")
                    self.selecionar_aba_imagem()
                else:
                    self.tipo_label.config(
                        text=f"Tipo: Desconhecido ({extensao.upper()})")

                # Definir pasta de destino padrão
                if not self.pasta_destino_var.get():
                    pasta_origem = os.path.dirname(arquivo)
                    self.pasta_destino_var.set(pasta_origem)

            else:
                self.tipo_label.config(
                    text="Selecione um arquivo para detectar o tipo")
        except Exception as e:
            self.tipo_label.config(text="Erro ao detectar tipo do arquivo")

    def selecionar_aba_audio(self):
        """Seleciona e exibe apenas a aba de áudio"""
        self.limpar_abas()
        self.notebook.add(self.aba_audio, text="Conversão de Áudio")
        self.notebook.select(self.aba_audio)
        self.modo_conversao_var.set("audio")

    def selecionar_aba_video(self):
        """Seleciona e exibe apenas a aba de vídeo"""
        self.limpar_abas()
        self.notebook.add(self.aba_video, text="Conversão de Vídeo")
        self.notebook.select(self.aba_video)
        self.modo_conversao_var.set("video")

    def selecionar_aba_imagem(self):
        """Seleciona e exibe apenas a aba de imagem"""
        self.limpar_abas()
        self.notebook.add(self.aba_imagem, text="Conversão de Imagem")
        self.notebook.select(self.aba_imagem)
        self.modo_conversao_var.set("imagem")

    def limpar_abas(self):
        """Remove todas as abas do notebook"""
        for i in range(self.notebook.index("end")):
            self.notebook.forget(0)

    def escolher_arquivo(self):
        """Abre diálogo para escolher arquivo de origem"""
        try:
            # Criar filtros para todos os tipos suportados
            todas_extensoes = []
            todas_extensoes.extend(self.extensoes_audio.keys())
            todas_extensoes.extend(self.extensoes_video.keys())
            todas_extensoes.extend(self.extensoes_imagem.keys())
            todas_extensoes.extend(self.extensoes_gif.keys())

            # Remover duplicatas e criar padrão
            todas_extensoes = list(set(todas_extensoes))
            padrao_todas = ";".join([f"*.{ext}" for ext in todas_extensoes])

            filetypes = [
                ("Todos os arquivos suportados", padrao_todas),
                ("Arquivos de áudio", ";".join(
                    [f"*.{ext}" for ext in self.extensoes_audio.keys()])),
                ("Arquivos de vídeo", ";".join(
                    [f"*.{ext}" for ext in self.extensoes_video.keys()])),
                ("Arquivos de imagem", ";".join(
                    [f"*.{ext}" for ext in list(self.extensoes_imagem.keys()) + list(self.extensoes_gif.keys())])),
                ("Todos os arquivos", "*.*")
            ]

            arquivo = filedialog.askopenfilename(
                title="Selecionar arquivo para converter",
                filetypes=filetypes
            )

            if arquivo:
                self.arquivo_origem_var.set(arquivo)

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao selecionar arquivo: {e}")

    def escolher_pasta(self):
        """Abre diálogo para escolher pasta de destino"""
        try:
            pasta = filedialog.askdirectory(
                title="Selecionar pasta de destino",
                initialdir=self.pasta_destino_var.get()
            )
            if pasta:
                self.pasta_destino_var.set(pasta)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao selecionar pasta: {e}")

    def cancelar_operacao(self):
        """Cancela a operação em andamento"""
        try:
            self.cancelar_conversao = True
            if self.processo_ativo:
                self.processo_ativo.terminate()

            self.progresso_label.config(text="Operação cancelada")
            self.barra_progresso.stop()
            self.botao_converter.config(state=tk.NORMAL)
            self.botao_cancelar.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao cancelar operação: {e}")

    def iniciar_conversao(self):
        """Inicia o processo de conversão"""
        try:
            # Validações
            arquivo_origem = self.arquivo_origem_var.get().strip()
            if not arquivo_origem or not os.path.isfile(arquivo_origem):
                messagebox.showerror(
                    "Erro", "Por favor, selecione um arquivo válido.")
                return

            pasta_destino = self.pasta_destino_var.get().strip()
            if not pasta_destino or not os.path.isdir(pasta_destino):
                messagebox.showerror(
                    "Erro", "Por favor, selecione uma pasta de destino válida.")
                return

            formato_destino = self.formato_destino_var.get()
            if not formato_destino:
                messagebox.showerror(
                    "Erro", "Por favor, selecione um formato de destino.")
                return

            # Verificar se não é conversão para o mesmo formato
            extensao_origem = arquivo_origem.lower().split('.')[-1]
            if extensao_origem == formato_destino.lower():
                resposta = messagebox.askyesno("Aviso",
                                               f"O arquivo já está no formato {formato_destino.upper()}. "
                                               "Deseja continuar mesmo assim? (Útil para alterar qualidade)")
                if not resposta:
                    return

            # Desativar botão durante a conversão
            self.botao_converter.config(state=tk.DISABLED)
            self.botao_cancelar.config(state=tk.NORMAL)
            self.progresso_label.config(text="Iniciando conversão...")
            self.barra_progresso.start()

            # Iniciar conversão em thread separada
            threading.Thread(target=self.executar_conversao,
                             daemon=True).start()

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao iniciar conversão: {e}")
            self.botao_converter.config(state=tk.NORMAL)

    def executar_conversao(self):
        """Executa a conversão com FFmpeg"""
        try:
            self.cancelar_conversao = False

            arquivo_origem = self.arquivo_origem_var.get()
            pasta_destino = self.pasta_destino_var.get()
            formato_destino = self.formato_destino_var.get()
            modo = self.modo_conversao_var.get()

            # Gerar nome do arquivo de saída
            nome_base = os.path.splitext(os.path.basename(arquivo_origem))[0]
            arquivo_destino = os.path.join(
                pasta_destino, f"{nome_base}.{formato_destino}")

            # Se arquivo já existe, criar versão numerada
            contador = 1
            arquivo_original = arquivo_destino
            while os.path.exists(arquivo_destino):
                nome_arquivo = f"{nome_base}_{contador}.{formato_destino}"
                arquivo_destino = os.path.join(pasta_destino, nome_arquivo)
                contador += 1

            # Obter comando FFmpeg
            ffmpeg_path = self.obter_ffmpeg_path()
            if not ffmpeg_path:
                raise Exception("FFmpeg não encontrado")

            comando = [ffmpeg_path, "-i", arquivo_origem]

            # Configurações específicas por tipo
            if modo == "audio":
                self.configurar_comando_audio(comando, formato_destino)
            elif modo == "video":
                self.configurar_comando_video(comando, formato_destino)
            elif modo == "imagem":
                self.configurar_comando_imagem(comando, formato_destino)

            # Adicionar arquivo de saída
            comando.extend(["-y", arquivo_destino])  # -y para sobrescrever

            self.root.after(0, lambda: self.progresso_label.config(
                text="Convertendo arquivo..."))

            # Executar comando
            self.processo_ativo = subprocess.Popen(
                comando,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Aguardar conclusão
            stdout, stderr = self.processo_ativo.communicate()
            codigo_saida = self.processo_ativo.returncode

            if self.cancelar_conversao:
                if os.path.exists(arquivo_destino):
                    os.remove(arquivo_destino)
                self.root.after(0, lambda: self.progresso_label.config(
                    text="Conversão cancelada"))
                return

            if codigo_saida == 0:
                self.root.after(0, lambda: self.progresso_label.config(
                    text="Conversão concluída com sucesso!"))
                self.root.after(0, lambda: messagebox.showinfo("Sucesso",
                                                               f"Arquivo convertido com sucesso!\nSalvo como: {os.path.basename(arquivo_destino)}"))
            else:
                error_msg = stderr.strip() if stderr else "Erro desconhecido"
                self.root.after(0, lambda: self.progresso_label.config(
                    text="Erro na conversão"))
                self.root.after(0, lambda: messagebox.showerror("Erro",
                                                                f"Erro durante a conversão:\n{error_msg[:200]}..."))

        except Exception as e:
            self.root.after(0, lambda: self.progresso_label.config(
                text=f"Erro: {str(e)[:50]}..."))
            self.root.after(0, lambda: messagebox.showerror(
                "Erro", f"Ocorreu um erro: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.barra_progresso.stop())
            self.root.after(
                0, lambda: self.botao_converter.config(state=tk.NORMAL))
            self.root.after(
                0, lambda: self.botao_cancelar.config(state=tk.DISABLED))
            self.processo_ativo = None

    def configurar_comando_audio(self, comando, formato_destino):
        """Configura comando FFmpeg para conversão de áudio"""
        qualidade = self.qualidade_var.get()

        if qualidade != "Manter Original":
            if "320kbps" in qualidade:
                comando.extend(["-b:a", "320k"])
            elif "256kbps" in qualidade:
                comando.extend(["-b:a", "256k"])
            elif "192kbps" in qualidade:
                comando.extend(["-b:a", "192k"])
            elif "128kbps" in qualidade:
                comando.extend(["-b:a", "128k"])
            elif "96kbps" in qualidade:
                comando.extend(["-b:a", "96k"])
            elif "64kbps" in qualidade:
                comando.extend(["-b:a", "64k"])

        # Configurações específicas por formato de áudio
        if formato_destino == "flac":
            comando.extend(["-c:a", "flac"])
        elif formato_destino == "wav":
            comando.extend(["-c:a", "pcm_s16le"])
        elif formato_destino == "mp3":
            comando.extend(["-c:a", "libmp3lame"])
        elif formato_destino == "aac":
            comando.extend(["-c:a", "aac"])
        elif formato_destino == "ogg":
            comando.extend(["-c:a", "libvorbis"])
        elif formato_destino == "opus":
            comando.extend(["-c:a", "libopus"])
        elif formato_destino == "m4a":
            comando.extend(["-c:a", "aac"])
        elif formato_destino == "alac":
            comando.extend(["-c:a", "alac"])

    def configurar_comando_video(self, comando, formato_destino):
        """Configura comando FFmpeg para conversão de vídeo"""
        qualidade = self.qualidade_var.get()

        # Configurações de resolução
        if qualidade != "Manter Original":
            if "4K" in qualidade:
                comando.extend(["-vf", "scale=3840:2160"])
            elif "1080p" in qualidade:
                comando.extend(["-vf", "scale=1920:1080"])
            elif "720p" in qualidade:
                comando.extend(["-vf", "scale=1280:720"])
            elif "480p" in qualidade:
                comando.extend(["-vf", "scale=854:480"])
            elif "360p" in qualidade:
                comando.extend(["-vf", "scale=640:360"])

        # Configurações específicas por formato de vídeo
        if formato_destino == "mp4":
            comando.extend(["-c:v", "libx264", "-c:a", "aac"])
        elif formato_destino == "mkv":
            comando.extend(["-c:v", "libx264", "-c:a", "aac"])
        elif formato_destino == "avi":
            comando.extend(["-c:v", "libx264", "-c:a", "mp3"])
        elif formato_destino == "webm":
            comando.extend(["-c:v", "libvpx-vp9", "-c:a", "libopus"])
        elif formato_destino == "mov":
            comando.extend(["-c:v", "libx264", "-c:a", "aac"])
        elif formato_destino == "flv":
            comando.extend(["-c:v", "libx264", "-c:a", "aac"])
        elif formato_destino == "wmv":
            comando.extend(["-c:v", "wmv2", "-c:a", "wmav2"])

        # Configurações gerais de qualidade para vídeo
        comando.extend(["-crf", "23", "-preset", "medium"])

    def configurar_comando_imagem(self, comando, formato_destino):
        """Configura comando FFmpeg para conversão de imagem"""
        qualidade = self.qualidade_var.get()

        # Configurações específicas por formato de imagem
        if formato_destino.lower() in ["jpg", "jpeg"]:
            # Configurar qualidade JPEG
            if "100%" in qualidade:
                comando.extend(["-q:v", "1"])
            elif "90%" in qualidade:
                comando.extend(["-q:v", "2"])
            elif "75%" in qualidade:
                comando.extend(["-q:v", "5"])
            elif "60%" in qualidade:
                comando.extend(["-q:v", "10"])
            elif "40%" in qualidade:
                comando.extend(["-q:v", "15"])
        elif formato_destino == "png":
            comando.extend(["-c:v", "png"])
        elif formato_destino == "bmp":
            comando.extend(["-c:v", "bmp"])
        elif formato_destino == "tiff":
            comando.extend(["-c:v", "tiff"])
        elif formato_destino == "webp":
            comando.extend(["-c:v", "libwebp"])
        elif formato_destino == "ico":
            comando.extend(["-vf", "scale=256:256"])

        # Para GIFs animados
        if formato_destino == "gif":
            comando.extend(["-vf", "fps=10,scale=320:-1:flags=lanczos"])


def main():
    """Função principal para executar o aplicativo"""
    try:
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('conversor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

        # Criar janela principal
        root = tk.Tk()

        # Tentar definir ícone da janela
        try:
            if os.path.exists("icon.ico"):
                root.iconbitmap("icon.ico")
        except:
            pass

        # Criar aplicativo
        app = FileConverter(root)

        # Configurar evento de fechamento
        def on_closing():
            if app.processo_ativo:
                if messagebox.askokcancel("Fechar", "Uma conversão está em andamento. Deseja cancelar e sair?"):
                    app.cancelar_operacao()
                    root.destroy()
            else:
                root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_closing)

        # Executar aplicativo
        root.mainloop()

    except Exception as e:
        messagebox.showerror(
            "Erro Fatal", f"Erro ao inicializar aplicativo: {e}")
        logging.error(f"Erro fatal: {e}")


if __name__ == "__main__":
    main()
# fim
