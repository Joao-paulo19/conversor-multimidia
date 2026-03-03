import os
import sys
import re
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import logging
from pathlib import Path

# Configuração de suporte para formatos adicionais e mapeamento
EXTENSOES_AUDIO = {
    'mp3': 'MPEG Layer III', 'wav': 'Waveform Audio', 'flac': 'Free Lossless Audio',
    'aac': 'Advanced Audio Codec', 'ogg': 'Ogg Vorbis', 'm4a': 'MPEG-4 Audio',
    'opus': 'Opus', 'alac': 'Apple Lossless Audio'
}

# GIF, WebP e APNG adicionados como vídeo para reconhecimento automático
EXTENSOES_VIDEO = {
    'mp4': 'MPEG-4 Part 14', 'mkv': 'Matroska Video', 'avi': 'Audio Video Interleave',
    'mov': 'QuickTime Movie', 'webm': 'Web Media', 'flv': 'Flash Video',
    'wmv': 'Windows Media Video', 'ts': 'MPEG Transport Stream',
    'gif': 'GIF Animado', 'webp': 'WebP Animado', 'apng': 'Animated PNG'
}

# Mantidos aqui para quando o foco for conversão de imagem estática
EXTENSOES_IMAGEM = {
    'jpg': 'JPEG Image', 'jpeg': 'JPEG Image', 'jfif': 'JPEG File Interchange Format',
    'png': 'Portable Network Graphics', 'bmp': 'Bitmap Image', 'webp': 'WebP Image',
    'tiff': 'TIFF Image', 'ico': 'Icon File', 'gif': 'GIF Image', 'apng': 'APNG Image'
}

QUALIDADES_AUDIO = [
    "Manter Original", "320kbps (Alta)", "256kbps (Alta)",
    "192kbps (Média)", "128kbps (Padrão)", "64kbps (Baixa)"
]

QUALIDADES_VIDEO = [
    "Manter Original", "4K (2160p)", "1080p (Full HD)",
    "720p (HD)", "480p (SD)", "360p (SD Baixa)"
]


class FileConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("Conversor Multimídia")
        self.root.geometry("800x700")
        self.root.configure(bg="#f5f5f5")

        # Variáveis de Estado
        self.arquivo_origem_var = tk.StringVar()
        self.pasta_destino_var = tk.StringVar()
        self.formato_destino_var = tk.StringVar()
        self.qualidade_var = tk.StringVar()
        self.modo_ativo = tk.StringVar(value="video")

        self.processo_ativo = None
        self.cancelar_conversao = False

        if not self.verificar_dependencias():
            messagebox.showerror(
                "Erro Crítico", "FFmpeg/FFprobe não encontrados no sistema ou pasta local.")
            self.root.destroy()
            return

        self.setup_ui()

    def recurso_caminho(self, relativo):
        """Busca caminhos para PyInstaller ou execução local"""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        caminho = os.path.join(base_path, relativo)
        if os.path.exists(caminho):
            return caminho
        return shutil.which(relativo.replace('.exe', '')) if os.name == 'nt' else shutil.which(relativo)

    def verificar_dependencias(self):
        import shutil
        ffmpeg = self.recurso_caminho("ffmpeg.exe") or shutil.which("ffmpeg")
        ffprobe = self.recurso_caminho(
            "ffprobe.exe") or shutil.which("ffprobe")
        return ffmpeg is not None and ffprobe is not None

    def obter_ffmpeg_path(self):
        import shutil
        return self.recurso_caminho("ffmpeg.exe") or shutil.which("ffmpeg")

    def detectar_tipo_arquivo(self, caminho):
        """Detecta o tipo priorizando a aba atual se for formato híbrido"""
        ext = caminho.lower().split('.')[-1]
        aba_atual = self.modo_ativo.get()
        # Formatos híbridos: se o usuário já estiver na aba de vídeo/imagem, mantém a preferência
        if ext in ['gif', 'webp', 'apng']:
            return aba_atual if aba_atual in ['video', 'imagem'] else "video"
        if ext in EXTENSOES_AUDIO:
            return "audio"
        if ext in EXTENSOES_VIDEO:
            return "video"
        if ext in EXTENSOES_IMAGEM:
            return "imagem"
        return "desconhecido"

    def setup_ui(self):
        # Estilização
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#f5f5f5")
        style.configure("TLabel", background="#f5f5f5", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Action.TButton", font=("Segoe UI", 10, "bold"))

        self.main_container = ttk.Frame(self.root, padding="20")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Header
        header = ttk.Label(
            self.main_container, text="Conversor de Arquivos Multimídia", style="Header.TLabel")
        header.pack(pady=(0, 20))

        # Seção de Seleção de Arquivo
        file_frame = ttk.LabelFrame(
            self.main_container, text=" 1. Seleção de Arquivo ", padding="10")
        file_frame.pack(fill=tk.X, pady=5)

        self.ent_origem = ttk.Entry(
            file_frame, textvariable=self.arquivo_origem_var)
        self.ent_origem.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        btn_procurar = ttk.Button(
            file_frame, text="Procurar", command=self.selecionar_arquivo)
        btn_procurar.pack(side=tk.RIGHT)

        # Label de Info do Arquivo
        self.lbl_info_arquivo = ttk.Label(
            self.main_container, text="Nenhum arquivo selecionado", foreground="#666")
        self.lbl_info_arquivo.pack(fill=tk.X, pady=2)

        # Container de Abas (Notebook)
        self.tabs = ttk.Notebook(self.main_container)
        self.tabs.pack(fill=tk.BOTH, expand=True, pady=15)

        # Criação das Abas
        self.tab_video = ttk.Frame(self.tabs, padding="15")
        self.tab_audio = ttk.Frame(self.tabs, padding="15")
        self.tab_imagem = ttk.Frame(self.tabs, padding="15")

        self.tabs.add(self.tab_video, text="  VÍDEOS  ")
        self.tabs.add(self.tab_audio, text="  ÁUDIOS  ")
        self.tabs.add(self.tab_imagem, text="  IMAGENS  ")

        self.build_tab_video()
        self.build_tab_audio()
        self.build_tab_imagem()

        self.tabs.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # Destino e Configurações Finais
        dest_frame = ttk.LabelFrame(
            self.main_container, text=" 2. Destino da Conversão ", padding="10")
        dest_frame.pack(fill=tk.X, pady=5)

        ttk.Label(dest_frame, text="Pasta de Saída:").pack(anchor=tk.W)
        dest_inner = ttk.Frame(dest_frame)
        dest_inner.pack(fill=tk.X)

        ttk.Entry(dest_inner, textvariable=self.pasta_destino_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(dest_inner, text="Alterar",
                   command=self.selecionar_pasta).pack(side=tk.RIGHT)

    def build_tab_video(self):
        ttk.Label(self.tab_video, text="Formato de Saída:").grid(
            row=0, column=0, sticky=tk.W, pady=5)
        self.cb_video_fmt = ttk.Combobox(self.tab_video, values=list(
            EXTENSOES_VIDEO.keys()), state="readonly")
        self.cb_video_fmt.grid(row=0, column=1, sticky=tk.EW, padx=5)
        self.cb_video_fmt.set("mp4")

        ttk.Label(self.tab_video, text="Resolução:").grid(
            row=1, column=0, sticky=tk.W, pady=5)
        self.cb_video_qual = ttk.Combobox(
            self.tab_video, values=QUALIDADES_VIDEO, state="readonly")
        self.cb_video_qual.grid(row=1, column=1, sticky=tk.EW, padx=5)
        self.cb_video_qual.set(QUALIDADES_VIDEO[0])

        info_vid = ttk.Label(self.tab_video, text="Dica: MP4 para GIF usa otimização via paleta de cores.", font=(
            "Segoe UI", 8), foreground="#777")
        info_vid.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=10)

    def build_tab_audio(self):
        ttk.Label(self.tab_audio, text="Formato de Saída:").grid(
            row=0, column=0, sticky=tk.W, pady=5)
        self.cb_audio_fmt = ttk.Combobox(self.tab_audio, values=list(
            EXTENSOES_AUDIO.keys()), state="readonly")
        self.cb_audio_fmt.grid(row=0, column=1, sticky=tk.EW, padx=5)
        self.cb_audio_fmt.set("mp3")

        ttk.Label(self.tab_audio, text="Bitrate:").grid(
            row=1, column=0, sticky=tk.W, pady=5)
        self.cb_audio_qual = ttk.Combobox(
            self.tab_audio, values=QUALIDADES_AUDIO, state="readonly")
        self.cb_audio_qual.grid(row=1, column=1, sticky=tk.EW, padx=5)
        self.cb_audio_qual.set(QUALIDADES_AUDIO[0])

    def build_tab_imagem(self):
        ttk.Label(self.tab_imagem, text="Formato de Saída:").grid(
            row=0, column=0, sticky=tk.W, pady=5)
        img_formats = list(EXTENSOES_IMAGEM.keys())
        self.cb_img_fmt = ttk.Combobox(
            self.tab_imagem, values=img_formats, state="readonly")
        self.cb_img_fmt.grid(row=0, column=1, sticky=tk.EW, padx=5)
        self.cb_img_fmt.set("png")
        ttk.Label(self.tab_imagem, text="Qualidade/Compressão:").grid(row=1,
                                                                      column=0, sticky=tk.W, pady=5)
        self.cb_img_qual = ttk.Combobox(self.tab_imagem, values=[
                                        "Alta (90%)", "Média (75%)", "Baixa (50%)"], state="readonly")
        self.cb_img_qual.grid(row=1, column=1, sticky=tk.EW, padx=5)
        self.cb_img_qual.set("Alta (90%)")

        lbl_jfif_note = ttk.Label(
            self.tab_imagem, text="Suporte total a .jfif (entrada/saída).", font=("Segoe UI", 8), foreground="#777")
        lbl_jfif_note.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=10)

        # 3. Barra de Progresso e Status
        status_frame = ttk.LabelFrame(
            self.main_container, text=" 3. Status da Operação ", padding="10")
        status_frame.pack(fill=tk.X, pady=10)

        self.lbl_status = ttk.Label(
            status_frame, text="Aguardando seleção de arquivo...")
        self.lbl_status.pack(fill=tk.X)

        self.progress_bar = ttk.Progressbar(
            status_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)

        # 4. Botões de Ação
        actions_frame = ttk.Frame(self.main_container)
        actions_frame.pack(fill=tk.X, pady=10)

        self.btn_cancelar = ttk.Button(
            actions_frame, text="CANCELAR", state=tk.DISABLED, command=self.cancelar_operacao)
        self.btn_cancelar.pack(side=tk.RIGHT, padx=5)

        self.btn_converter = ttk.Button(
            actions_frame, text="INICIAR CONVERSÃO", style="Action.TButton", command=self.iniciar_thread_conversao)
        self.btn_converter.pack(side=tk.RIGHT, padx=5)

        # Configurações de Log Interno
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

    def on_tab_change(self, event):
        """Atualiza o modo ativo baseado na aba selecionada"""
        tab_index = self.tabs.index(self.tabs.select())
        if tab_index == 0:
            self.modo_ativo.set("video")
        elif tab_index == 1:
            self.modo_ativo.set("audio")
        elif tab_index == 2:
            self.modo_ativo.set("imagem")
        self.atualizar_sugestao_extensao()

    def selecionar_arquivo(self):
        tipos = [
            ("Todos os suportados",
             "*.mp4 *.mkv *.avi *.mov *.webm *.mp3 *.wav *.flac *.jpg *.jpeg *.png *.jfif *.webp"),
            ("Vídeos", "*.mp4 *.mkv *.avi *.mov *.webm"),
            ("Áudios", "*.mp3 *.wav *.flac *.m4a"),
            ("Imagens", "*.jpg *.jpeg *.png *.jfif *.webp *.bmp"),
            ("Todos os arquivos", "*.*")
        ]

        arquivo = filedialog.askopenfilename(
            title="Selecionar arquivo para conversão", filetypes=tipos)

        if arquivo:
            self.arquivo_origem_var.set(arquivo)
            tipo_detectado = self.detectar_tipo_arquivo(arquivo)
            ext = arquivo.lower().split('.')[-1]

            self.lbl_info_arquivo.config(
                text=f"Selecionado: {os.path.basename(arquivo)} | Tipo: {tipo_detectado.upper()}")

            # Auto-selecionar a aba correta
            if tipo_detectado == "video":
                self.tabs.select(self.tab_video)
            elif tipo_detectado == "audio":
                self.tabs.select(self.tab_audio)
            elif tipo_detectado == "imagem":
                self.tabs.select(self.tab_imagem)

            if not self.pasta_destino_var.get():
                self.pasta_destino_var.set(os.path.dirname(arquivo))

            self.atualizar_sugestao_extensao()

    def selecionar_pasta(self):
        pasta = filedialog.askdirectory(title="Selecionar pasta de destino")
        if pasta:
            self.pasta_destino_var.set(pasta)

    def atualizar_sugestao_extensao(self):
        """Tenta prever a extensão de saída baseada na aba e entrada"""
        modo = self.modo_ativo.get()
        if not self.arquivo_origem_var.get():
            return

        # Lógica para evitar converter para a mesma extensão por acidente
        ext_origem = self.arquivo_origem_var.get().lower().split('.')[-1]

        if modo == "video":
            if ext_origem == "mp4":
                self.cb_video_fmt.set("mkv")
            else:
                self.cb_video_fmt.set("mp4")
        elif modo == "audio":
            if ext_origem == "mp3":
                self.cb_audio_fmt.set("wav")
            else:
                self.cb_audio_fmt.set("mp3")
        elif modo == "imagem":
            if ext_origem in ["jpg", "jpeg", "jfif"]:
                self.cb_img_fmt.set("png")
            else:
                self.cb_img_fmt.set("jpg")

    def cancelar_operacao(self):
        if self.processo_ativo:
            self.cancelar_conversao = True
            self.processo_ativo.terminate()
            self.lbl_status.config(
                text="Operação interrompida pelo usuário.", foreground="red")
            self.finalizar_ui_pos_conversao()

    def iniciar_thread_conversao(self):
        # Validações Iniciais
        origem = self.arquivo_origem_var.get()
        destino_dir = self.pasta_destino_var.get()

        if not origem or not os.path.exists(origem):
            messagebox.showerror(
                "Erro", "Selecione um arquivo de origem válido.")
            return
        if not destino_dir or not os.path.isdir(destino_dir):
            messagebox.showerror(
                "Erro", "Selecione uma pasta de destino válida.")
            return

        # Bloquear interface para evitar múltiplas execuções simultâneas
        self.btn_converter.config(state=tk.DISABLED)
        self.btn_cancelar.config(state=tk.NORMAL)
        self.progress_bar['value'] = 0
        self.cancelar_conversao = False

        # Disparo da execução em segundo plano para não travar a GUI
        threading.Thread(target=self.executar_conversao, daemon=True).start()

    def executar_conversao(self):
        """Núcleo do processamento: gerencia o ciclo de vida da execução do FFmpeg"""
        try:
            origem = self.arquivo_origem_var.get()
            destino_dir = self.pasta_destino_var.get()
            modo = self.modo_ativo.get()

            # Captura de parâmetros dinâmicos baseados no contexto da aba selecionada
            if modo == "video":
                formato = self.cb_video_fmt.get()
                qualidade = self.cb_video_qual.get()
            elif modo == "audio":
                formato = self.cb_audio_fmt.get()
                qualidade = self.cb_audio_qual.get()
            else:
                formato = self.cb_img_fmt.get()
                qualidade = self.cb_img_qual.get()

            # Construção do nome do arquivo de saída com proteção contra duplicatas
            nome_base = Path(origem).stem
            saida = os.path.join(destino_dir, f"{nome_base}.{formato}")

            count = 1
            while os.path.exists(saida):
                saida = os.path.join(
                    destino_dir, f"{nome_base}_{count}.{formato}")
                count += 1

            ffmpeg_path = self.obter_ffmpeg_path()
            # Comando base com supressão de banner para logs limpos
            comando = [ffmpeg_path, "-hide_banner", "-i", origem]

            # Injeção de parâmetros específicos por tipo de mídia
            if modo == "video":
                self.configurar_comando_video(comando, formato, qualidade)
            elif modo == "audio":
                self.configurar_comando_audio(comando, formato, qualidade)
            elif modo == "imagem":
                self.configurar_comando_imagem(comando, formato, qualidade)

            # Adição do parâmetro de saída e sobrescrita forçada (controle manual via código)
            comando.extend(["-y", saida])

            logging.info(f"Comando Gerado: {' '.join(comando)}")
            self.root.after(0, lambda: self.lbl_status.config(
                text="Convertendo... Por favor, aguarde.", foreground="#0056b3"))

            # Inicialização do subprocesso capturando stdout/stderr para monitoramento
            self.processo_ativo = subprocess.Popen(
                comando,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Monitoramento em tempo real da saída do FFmpeg para atualizar a barra de progresso
            while True:
                linha = self.processo_ativo.stdout.readline()
                if not linha and self.processo_ativo.poll() is not None:
                    break

                if self.cancelar_conversao:
                    break

                # Incremento visual baseado nos frames processados reportados pelo FFmpeg
                if "frame=" in linha or "size=" in linha or "time=" in linha:
                    self.root.after(0, lambda: self.progress_bar.step(0.2))

            self.processo_ativo.wait()

            # Limpeza e tratamento em caso de interrupção pelo usuário
            if self.cancelar_conversao:
                if os.path.exists(saida):
                    try:
                        os.remove(saida)
                    except:
                        pass
                self.root.after(0, lambda: self.lbl_status.config(
                    text="Conversão cancelada.", foreground="orange"))
                return

            # Validação do resultado final da execução
            if self.processo_ativo.returncode == 0:
                self.root.after(0, lambda: self.lbl_status.config(
                    text="Concluído com sucesso!", foreground="green"))
                self.root.after(0, lambda: messagebox.showinfo(
                    "Sucesso", f"Arquivo gerado:\n{os.path.basename(saida)}"))
            else:
                self.root.after(0, lambda: self.lbl_status.config(
                    text="Falha técnica na conversão.", foreground="red"))
                self.root.after(0, lambda: messagebox.showerror(
                    "Erro FFmpeg", "O FFmpeg encontrou um erro. Verifique a integridade do arquivo de origem."))

        except Exception as e:
            logging.critical(f"Erro fatal na thread de execução: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Erro de Sistema", f"Falha interna crítica: {str(e)}"))
        finally:
            self.root.after(0, self.finalizar_ui_pos_conversao)

    def configurar_comando_video(self, comando, formato, qualidade):
        """Define os parâmetros de transcodificação de vídeo e otimização de GIFs"""
        filtros = []

        # Mapeamento de resoluções para o filtro de escala (scale)
        res_map = {
            "4K (2160p)": "3840:2160",
            "1080p (Full HD)": "1920:1080",
            "720p (HD)": "1280:720",
            "480p (SD)": "854:480",
            "360p (SD Baixa)": "640:360"
        }

        if qualidade in res_map:
            # Filtro para redimensionamento respeitando o aspect ratio (padding para evitar distorção)
            w, h = res_map[qualidade].split(':')
            filtros.append(
                f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")

        if formato == "gif":
            # Técnica avançada de Paleta de Cores para GIFs de alta fidelidade
            # Reduzimos o FPS para 12 para garantir equilíbrio entre fluidez e tamanho de arquivo
            fps_val = "12"
            scale_val = "480:-1"  # Resolução mobile-friendly por padrão para GIFs

            # Filtro complexo: gera paleta global e aplica para evitar pontilhado excessivo
            gif_filter = f"fps={fps_val},scale={scale_val}:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
            # -an remove fluxos de áudio incompatíveis
            comando.extend(["-vf", gif_filter, "-an"])
        else:
            # Aplicação de filtros de vídeo gerais
            if filtros:
                comando.extend(["-vf", ",".join(filtros)])

            # Seleção de codecs baseada no container de destino
            if formato == "webm":
                comando.extend(["-c:v", "libvpx-vp9", "-crf",
                               "30", "-b:v", "0", "-c:a", "libopus"])
            elif formato == "avi":
                comando.extend(["-c:v", "libx264", "-c:a", "libmp3lame"])
            elif formato == "wmv":
                comando.extend(["-c:v", "wmv2", "-c:a", "wmav2"])
            else:
                # Perfil padrão (H.264 + AAC) para MP4, MKV e MOV
                comando.extend(["-c:v", "libx264", "-preset", "medium",
                               "-crf", "23", "-c:a", "aac", "-b:a", "192k"])

    def configurar_comando_audio(self, comando, formato, qualidade):
        """Implementa a lógica de bitrate e codecs para áudio puro"""
        bitrates = {
            "320kbps (Alta)": "320k", "256kbps (Alta)": "256k",
            "192kbps (Média)": "192k", "128kbps (Padrão)": "128k", "64kbps (Baixa)": "64k"
        }

        if qualidade in bitrates:
            comando.extend(["-b:a", bitrates[qualidade]])

        # Mapeamento de Codecs por Formato
        if formato == "flac":
            comando.extend(["-c:a", "flac"])
        elif formato == "wav":
            comando.extend(["-c:a", "pcm_s16le"])
        elif formato == "aac" or formato == "m4a":
            comando.extend(["-c:a", "aac"])
        elif formato == "ogg":
            comando.extend(["-c:a", "libvorbis"])
        elif formato == "opus":
            comando.extend(["-c:a", "libopus"])
        elif formato == "alac":
            comando.extend(["-c:a", "alac"])
        else:
            comando.extend(["-c:a", "libmp3lame"])

    def configurar_comando_imagem(self, comando, formato, qualidade):
        """Lógica para imagens estáticas, suporte JFIF e conversão de GIF/WebP para MP4"""
        ext_origem = self.arquivo_origem_var.get().lower().split('.')[-1]

        # Caso especial: Conversão de GIF animado ou WebP animado para Vídeo (MP4)
        if (ext_origem in ['gif', 'webp']) and formato == 'mp4':
            comando.extend([
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-movflags", "+faststart"
            ])
            return

        # Tratamento de qualidade para formatos baseados em JPEG (incluindo JFIF)
        if formato in ["jpg", "jpeg", "jfif"]:
            q_val = "2"  # Padrão Alta
            if "90%" in qualidade:
                q_val = "2"
            elif "75%" in qualidade:
                q_val = "5"
            elif "50%" in qualidade:
                q_val = "10"
            comando.extend(["-q:v", q_val])

        # Configurações de Codecs de Imagem
        if formato == "png":
            comando.extend(["-c:v", "png"])
        elif formato == "webp":
            comando.extend(["-c:v", "libwebp", "-lossless",
                           "0", "-compression_level", "6"])
        elif formato == "bmp":
            comando.extend(["-c:v", "bmp"])
        elif formato == "tiff":
            comando.extend(["-c:v", "tiff"])
        elif formato == "ico":
            comando.extend(["-vf", "scale=256:256"])

    def finalizar_ui_pos_conversao(self):
        """Restaura o estado dos widgets após o término do processo"""
        self.btn_converter.config(state=tk.NORMAL)
        self.btn_cancelar.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self.processo_ativo = None

    def obter_metadados(self, arquivo):
        """Utiliza FFprobe para extrair informações técnicas do arquivo"""
        try:
            ffprobe_path = self.recurso_caminho(
                "ffprobe.exe") or shutil.which("ffprobe")
            cmd = [
                ffprobe_path, "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", arquivo
            ]
            resultado = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT).decode('utf-8')
            import json
            return json.loads(resultado)
        except:
            return None


def main():
    """Inicialização do Loop Principal"""
    logging.info("Iniciando Aplicativo...")
    root = tk.Tk()

    # Configuração de Estilo Global
    try:
        if os.name == 'nt':
            root.iconbitmap(default=None)  # Placeholder para ícone customizado
    except:
        pass

    app = FileConverter(root)

    def fechar_janela():
        if app.processo_ativo:
            if messagebox.askokcancel("Sair", "Uma conversão está em andamento. Deseja realmente cancelar e sair?"):
                app.cancelar_operacao()
                root.destroy()
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", fechar_janela)
    root.mainloop()

# Início da Seção de Utilidades de Frame e UI helper


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 27
        y = y + cy + self.widget.winfo_rooty() + 27
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

# Estendendo funcionalidades para logs detalhados


class ScrollableTextHandler(logging.Handler):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def emit(self, record):
        msg = self.format(record)

        def append():
            self.widget.configure(state='normal')
            self.widget.insert(tk.END, msg + '\n')
            self.widget.configure(state='disabled')
            self.widget.see(tk.END)
        self.widget.after(0, append)

    def emit(self, record):
        """Redireciona mensagens de log para um widget de texto se disponível"""
        msg = self.format(record)

        def append():
            try:
                self.widget.configure(state='normal')
                self.widget.insert(tk.END, msg + '\n')
                self.widget.configure(state='disabled')
                self.widget.see(tk.END)
            except:
                pass
        if self.widget:
            self.widget.after(0, append)

# Seção de Tratamento de Erros e Compatibilidade de Formatos


def validar_nome_arquivo(nome):
    """Remove caracteres inválidos para sistemas de arquivos"""
    return re.sub(r'[<>:"/\\|?*]', '', nome)


def obter_extensao_real(caminho):
    """Retorna a extensão em minúsculas sem o ponto"""
    return os.path.splitext(caminho)[1][1:].lower()

# Funções de suporte para o suporte JFIF e conversão de imagem


def configurar_imagem_jfif(caminho_origem, caminho_saida, qualidade):
    """
    Nota técnica: O FFmpeg trata JFIF como uma variante do JPEG.
    Esta função garante que o codec correto seja aplicado para manter a 
    compatibilidade do cabeçalho JFIF durante a transcodificação.
    """
    params = ["-i", caminho_origem]
    if "90%" in qualidade:
        params.extend(["-q:v", "2"])
    elif "75%" in qualidade:
        params.extend(["-q:v", "5"])
    else:
        params.extend(["-q:v", "10"])
    return params

# Finalização do Módulo de Interface e Widgets Auxiliares


class CustomButton(tk.Button):
    """Subclasse de botão para efeitos visuais básicos (Hover)"""

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, event):
        self['background'] = '#e1e1e1'

    def on_leave(self, event):
        self['background'] = '#f0f0f0'


# Ponto de Entrada do Sistema
if __name__ == "__main__":
    # Configuração de diretórios temporários para o FFmpeg se necessário
    os.environ["TMPDIR"] = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp") \
        if os.name == 'nt' else "/tmp"

    try:
        # Verifica se o FFmpeg está acessível antes de subir a GUI
        import shutil
        if not shutil.which("ffmpeg") and not os.path.exists("ffmpeg.exe"):
            print("Aviso: FFmpeg não detectado no PATH ou diretório local.")

        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        logging.critical(f"Falha ao iniciar aplicação: {e}")
        messagebox.showerror(
            "Erro Fatal", f"Ocorreu um erro ao iniciar o programa:\n{e}")

# FIM DO ARQUIVO - CONVERSOR MULTIMÍDIA REESTRUTURADO
