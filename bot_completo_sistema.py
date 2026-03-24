"""
🎮 BOT APOSTAS FREE FIRE - SISTEMA COMPLETO
Com Canais Privados, Admin Panel, Logs e Confirmação
"""

import discord
from discord.ext import commands
from discord import app_commands, ui
import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, List

# ============================================
# CONFIGURAÇÃO BOT
# ============================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# ============================================
# CORES
# ============================================

COR_PRINCIPAL = discord.Color.from_rgb(220, 38, 38)  # Vermelho
COR_SUCESSO = discord.Color.from_rgb(34, 197, 94)   # Verde
COR_AVISO = discord.Color.from_rgb(234, 179, 8)     # Amarelo
COR_DANGER = discord.Color.from_rgb(239, 68, 68)    # Vermelho claro

# ============================================
# DADOS GLOBAIS
# ============================================

class Jogador:
    def __init__(self, user_id: int, nome: str, estilo: str):
        self.user_id = user_id
        self.nome = nome
        self.estilo = estilo
        self.mention = f"<@{user_id}>"

class ConfigBot:
    """Armazena configurações do bot"""
    def __init__(self):
        self.canal_log = None  # ID do canal de logs
        self.canal_aceitar = None  # ID do canal de aceitar fila
        self.categorias = {}  # tamanho -> category_id
        self.admin_ids = set()  # IDs dos admins

config = ConfigBot()

class GerenciadorFilas:
    def __init__(self):
        self.filas_ativas = {}  # painel_id -> config da fila
        self.partidas = {}  # game_id -> info da partida
        self.canais_partidas = {}  # game_id -> channel_id
        self.blacklist = set()
        self.admins_sala = {}  # game_id -> admin_id responsável

gerenciador = GerenciadorFilas()

# ============================================
# EVENTOS
# ============================================

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} conectado!")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos sincronizados")
    except Exception as e:
        print(f"❌ Erro: {e}")

# ============================================
# CONFIGURAÇÃO DO BOT
# ============================================

@bot.tree.command(name="config_bot", description="⚙️ Configurar canais do bot")
@app_commands.describe(
    canal_log="Canal para logs de filas",
    canal_aceitar="Canal para aceitar filas"
)
async def config_bot(
    interaction: discord.Interaction,
    canal_log: discord.TextChannel,
    canal_aceitar: discord.TextChannel
):
    """Configura os canais do bot"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Apenas administradores!", ephemeral=True)
        return

    config.canal_log = canal_log.id
    config.canal_aceitar = canal_aceitar.id

    embed = discord.Embed(
        title="✅ Configuração Salva",
        color=COR_SUCESSO
    )
    embed.add_field(name="📋 Canal de Log", value=canal_log.mention, inline=False)
    embed.add_field(name="✅ Canal de Aceitar", value=canal_aceitar.mention, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="config_categoria", description="📁 Configurar categoria para um tamanho de jogo")
@app_commands.describe(
    tamanho="Tamanho do jogo (1v1, 2v2, 3v3, 4v4)",
    categoria="Categoria do Discord onde criar os canais"
)
@app_commands.choices(
    tamanho=[
        app_commands.Choice(name="1v1", value="1v1"),
        app_commands.Choice(name="2v2", value="2v2"),
        app_commands.Choice(name="3v3", value="3v3"),
        app_commands.Choice(name="4v4", value="4v4"),
    ]
)
async def config_categoria(
    interaction: discord.Interaction,
    tamanho: str,
    categoria: discord.CategoryChannel
):
    """Configura a categoria para criar canais de partida"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Apenas administradores!", ephemeral=True)
        return

    config.categorias[tamanho] = categoria.id

    embed = discord.Embed(
        title="✅ Categoria Configurada",
        color=COR_SUCESSO
    )
    embed.add_field(name="🎮 Tamanho", value=tamanho, inline=False)
    embed.add_field(name="📁 Categoria", value=categoria.mention, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="admin_add", description="👮 Adicionar admin ao bot")
async def admin_add(interaction: discord.Interaction, usuario: discord.User):
    """Adiciona um usuário como admin"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Apenas administradores!", ephemeral=True)
        return

    config.admin_ids.add(usuario.id)

    embed = discord.Embed(
        title="✅ Admin Adicionado",
        color=COR_SUCESSO
    )
    embed.add_field(name="👤 Usuário", value=usuario.mention, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================
# COMANDO /GENFILA
# ============================================

@bot.tree.command(name="genfila", description="🎮 Gerar um painel de fila customizado")
@app_commands.describe(
    tamanho="Tamanho do jogo: 1v1, 2v2, 3v3, 4v4",
    plataforma="Plataforma: Mobile, Emulador, Misto",
    valor="Valor da partida em R$",
    nome="Nome customizado da fila (opcional)"
)
@app_commands.choices(
    tamanho=[
        app_commands.Choice(name="1v1", value="1v1"),
        app_commands.Choice(name="2v2", value="2v2"),
        app_commands.Choice(name="3v3", value="3v3"),
        app_commands.Choice(name="4v4", value="4v4"),
    ],
    plataforma=[
        app_commands.Choice(name="📱 Mobile", value="mobile"),
        app_commands.Choice(name="💻 Emulador", value="emu"),
        app_commands.Choice(name="🖥️ Misto", value="misto"),
    ]
)
async def genfila(
    interaction: discord.Interaction,
    tamanho: str,
    plataforma: str,
    valor: float,
    nome: Optional[str] = None
):
    """Cria um painel de fila customizado"""
    await interaction.response.defer()

    if not config.canal_log or not config.canal_aceitar:
        await interaction.followup.send("❌ Bot não configurado! Use /config_bot primeiro", ephemeral=True)
        return

    # Emoji pela plataforma
    emoji_map = {
        "mobile": "📱",
        "emu": "💻",
        "misto": "🖥️"
    }
    emoji = emoji_map.get(plataforma, "🎮")

    # Nome da fila
    nome_fila = nome or f"{tamanho} {plataforma.capitalize()}"

    # ID único
    painel_id = str(uuid.uuid4())[:8]

    # Guardar configuração
    gerenciador.filas_ativas[painel_id] = {
        "tamanho": tamanho,
        "plataforma": plataforma,
        "valor": valor,
        "nome": nome_fila,
        "jogadores_normal": [],
        "jogadores_full_ump": [],
        "jogadores_mobilador": [],
        "painel_id": painel_id,
        "guild_id": interaction.guild.id
    }

    # Embed do painel (para o canal da fila)
    embed_painel = discord.Embed(
        title=f"{emoji} {nome_fila}",
        color=COR_PRINCIPAL
    )
    embed_painel.add_field(name="💰 Valor Partida", value=f"R$ {valor:.2f}", inline=False)
    embed_painel.add_field(name="⚙️ Modo", value=f"{tamanho} {plataforma.capitalize()}", inline=False)
    embed_painel.add_field(name="👥 Jogadores na fila", value="Nenhum jogador na fila.", inline=False)

    view_painel = ViewEntrarFila(painel_id, tamanho, plataforma, valor)

    # Enviar painel no canal de aceitar
    canal_aceitar = bot.get_channel(config.canal_aceitar)
    msg_painel = await canal_aceitar.send(embed=embed_painel, view=view_painel)
    gerenciador.filas_ativas[painel_id]["msg_painel_id"] = msg_painel.id

    # Embed de log
    embed_log = discord.Embed(
        title="📋 NOVA FILA CRIADA",
        color=COR_AVISO
    )
    embed_log.add_field(name="🎮 Tipo", value=f"{tamanho} {plataforma.capitalize()}", inline=False)
    embed_log.add_field(name="💰 Valor", value=f"R$ {valor:.2f}", inline=False)
    embed_log.add_field(name="🆔 ID", value=f"`{painel_id}`", inline=False)
    embed_log.add_field(name="👤 Criado por", value=interaction.user.mention, inline=False)
    embed_log.add_field(name="⏰ Horário", value=f"<t:{int(datetime.now().timestamp())}:T>", inline=False)
    embed_log.set_footer(text=f"ID: {painel_id}")

    canal_log = bot.get_channel(config.canal_log)
    await canal_log.send(embed=embed_log)

    # Confirmação
    embed_confirm = discord.Embed(
        title="✅ Fila Criada!",
        color=COR_SUCESSO
    )
    embed_confirm.add_field(name="🆔 ID", value=f"`{painel_id}`", inline=False)

    await interaction.followup.send(embed=embed_confirm, ephemeral=True)

# ============================================
# VIEWS COM BOTÕES
# ============================================

class ViewEntrarFila(ui.View):
    """View para entrar na fila"""
    def __init__(self, painel_id: str, tamanho: str, plataforma: str, valor: float):
        super().__init__(timeout=None)
        self.painel_id = painel_id
        self.tamanho = tamanho
        self.plataforma = plataforma
        self.valor = valor

    @ui.button(label="Normal", style=discord.ButtonStyle.gray, emoji="⚪")
    async def btn_normal(self, interaction: discord.Interaction, button: ui.Button):
        await entrar_fila(interaction, self.painel_id, "normal")

    @ui.button(label="Full Ump Xm8", style=discord.ButtonStyle.primary, emoji="🎯")
    async def btn_full_ump(self, interaction: discord.Interaction, button: ui.Button):
        await entrar_fila(interaction, self.painel_id, "full_ump")

    @ui.button(label="Mobilador", style=discord.ButtonStyle.success, emoji="🚀")
    async def btn_mobilador(self, interaction: discord.Interaction, button: ui.Button):
        await entrar_fila(interaction, self.painel_id, "mobilador")

    @ui.button(label="Sair", style=discord.ButtonStyle.danger, emoji="❌")
    async def btn_sair(self, interaction: discord.Interaction, button: ui.Button):
        await sair_fila(interaction, self.painel_id)

async def entrar_fila(interaction: discord.Interaction, painel_id: str, estilo: str):
    """Adiciona jogador à fila"""
    await interaction.response.defer(ephemeral=True)

    fila = gerenciador.filas_ativas.get(painel_id)
    if not fila:
        await interaction.followup.send("❌ Fila não encontrada!", ephemeral=True)
        return

    if interaction.user.id in gerenciador.blacklist:
        await interaction.followup.send("❌ Você está na blacklist!", ephemeral=True)
        return

    # Verificar se já está em fila
    for lista in [fila["jogadores_normal"], fila["jogadores_full_ump"], fila["jogadores_mobilador"]]:
        if any(j.user_id == interaction.user.id for j in lista):
            await interaction.followup.send("❌ Você já está em uma fila!", ephemeral=True)
            return

    jogador = Jogador(interaction.user.id, interaction.user.display_name, estilo)

    if estilo == "normal":
        lista_fila = fila["jogadores_normal"]
    elif estilo == "full_ump":
        lista_fila = fila["jogadores_full_ump"]
    else:
        lista_fila = fila["jogadores_mobilador"]

    tamanho = int(fila["tamanho"].split("v")[0])

    if len(lista_fila) == 0:
        lista_fila.append(jogador)
        embed = discord.Embed(
            title="⏳ AGUARDANDO OPONENTE",
            color=COR_AVISO
        )
        embed.add_field(name="Estilo", value=estilo.replace("_", " ").title(), inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    else:
        # Contar jogadores no mesmo estilo
        if len(lista_fila) < tamanho:
            lista_fila.append(jogador)
            embed = discord.Embed(
                title="⏳ AGUARDANDO OPONENTE",
                color=COR_AVISO
            )
            embed.add_field(name="Estilo", value=estilo.replace("_", " ").title(), inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            # Pareamento!
            await parear_jogadores(interaction, painel_id, estilo, fila, jogador, lista_fila)

    await atualizar_painel(painel_id)

async def parear_jogadores(interaction: discord.Interaction, painel_id: str, estilo: str, fila: dict, novo_jogador: Jogador, lista_fila: List[Jogador]):
    """Pareia jogadores e cria canal privado"""
    
    tamanho = int(fila["tamanho"].split("v")[0])

    # Separar times
    time1 = lista_fila[:tamanho]
    lista_fila.clear()  # Limpar fila após pareamento

    time2_list = [novo_jogador]

    # ID da partida
    game_id = str(uuid.uuid4())[:8]

    # Armazenar partida
    gerenciador.partidas[game_id] = {
        "id": game_id,
        "time1": time1,
        "time2": time2_list,
        "tamanho": fila["tamanho"],
        "plataforma": fila["plataforma"],
        "estilo": estilo,
        "valor": fila["valor"],
        "status": "aguardando_admin",
        "timestamp": datetime.now()
    }

    guild = interaction.guild
    categoria_id = config.categorias.get(fila["tamanho"])

    if not categoria_id:
        await interaction.followup.send(
            f"❌ Categoria não configurada para {fila['tamanho']}!\nUse /config_categoria",
            ephemeral=True
        )
        return

    categoria = guild.get_channel(categoria_id)

    # Criar canal privado
    nome_canal = f"partida-{game_id}".lower()
    
    # Permissões
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }

    # Adicionar jogadores ao canal
    for jogador in time1 + time2_list:
        usuario = await bot.fetch_user(jogador.user_id)
        overwrites[usuario] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    # Criar canal
    canal = await categoria.create_text_channel(
        nome_canal,
        overwrites=overwrites
    )

    gerenciador.canais_partidas[game_id] = canal.id

    # Embed da partida no canal
    embed_partida = discord.Embed(
        title="🎮 PARTIDA ENCONTRADA!",
        color=COR_SUCESSO
    )

    time1_mentions = " ".join([j.mention for j in time1])
    time2_mentions = " ".join([j.mention for j in time2_list])

    embed_partida.add_field(name="👥 TIME 1", value=time1_mentions, inline=True)
    embed_partida.add_field(name="👥 TIME 2", value=time2_mentions, inline=True)
    embed_partida.add_field(name="⚙️ Estilo", value=estilo.replace("_", " ").title(), inline=False)
    embed_partida.add_field(name="📊 Modo", value=f"{fila['tamanho']} {fila['plataforma'].capitalize()}", inline=False)
    embed_partida.add_field(name="💰 Valor", value=f"R$ {fila['valor']:.2f}", inline=False)
    embed_partida.add_field(name="🆔 ID", value=f"`{game_id}`", inline=False)
    embed_partida.set_footer(text="Aguardando confirmação do admin...")

    view_partida = ViewPartidaCanal(game_id)
    await canal.send(embed=embed_partida, view=view_partida)

    # Notificar no canal de aceitar
    embed_aceitar = discord.Embed(
        title="✅ FILA ENCONTRADA - CONFIRMAR",
        color=COR_SUCESSO
    )
    embed_aceitar.add_field(name="👥 TIME 1", value=time1_mentions, inline=False)
    embed_aceitar.add_field(name="👥 TIME 2", value=time2_mentions, inline=False)
    embed_aceitar.add_field(name="⚙️ Estilo", value=estilo.replace("_", " ").title(), inline=True)
    embed_aceitar.add_field(name="📊 Tamanho", value=fila['tamanho'], inline=True)
    embed_aceitar.add_field(name="💰 Valor", value=f"R$ {fila['valor']:.2f}", inline=True)
    embed_aceitar.add_field(name="🎮 Plataforma", value=fila['plataforma'].capitalize(), inline=True)
    embed_aceitar.add_field(name="🆔 ID", value=f"`{game_id}`", inline=False)
    embed_aceitar.add_field(name="🔗 Canal", value=canal.mention, inline=False)
    embed_aceitar.set_footer(text=f"ID: {game_id}")

    canal_aceitar = bot.get_channel(config.canal_aceitar)
    view_aceitar = ViewAceitarFila(game_id, canal.id)
    msg_aceitar = await canal_aceitar.send(embed=embed_aceitar, view=view_aceitar)

    # Log
    embed_log = discord.Embed(
        title="🎮 FILA ENCONTRADA",
        color=COR_SUCESSO
    )
    embed_log.add_field(name="👥 TIME 1", value=time1_mentions, inline=False)
    embed_log.add_field(name="👥 TIME 2", value=time2_mentions, inline=False)
    embed_log.add_field(name="🆔 ID Partida", value=f"`{game_id}`", inline=False)
    embed_log.add_field(name="⏰ Horário", value=f"<t:{int(datetime.now().timestamp())}:T>", inline=False)

    canal_log = bot.get_channel(config.canal_log)
    await canal_log.send(embed=embed_log)

    # Notificar jogadores
    embed_notif = discord.Embed(
        title="🎮 PARTIDA ENCONTRADA!",
        description="Um admin vai confirmar em breve...",
        color=COR_AVISO
    )
    embed_notif.add_field(name="🔗 Canal", value=canal.mention, inline=False)

    await interaction.followup.send(embed=embed_notif, ephemeral=True)

async def sair_fila(interaction: discord.Interaction, painel_id: str):
    """Remove jogador da fila"""
    await interaction.response.defer(ephemeral=True)

    fila = gerenciador.filas_ativas.get(painel_id)
    if not fila:
        await interaction.followup.send("❌ Fila não encontrada!", ephemeral=True)
        return

    removido = False
    for lista in [fila["jogadores_normal"], fila["jogadores_full_ump"], fila["jogadores_mobilador"]]:
        for jogador in lista:
            if jogador.user_id == interaction.user.id:
                lista.remove(jogador)
                removido = True
                break
        if removido:
            break

    if removido:
        await interaction.followup.send("❌ Removido da fila!", ephemeral=True)
        await atualizar_painel(painel_id)
    else:
        await interaction.followup.send("❌ Você não está em nenhuma fila!", ephemeral=True)

async def atualizar_painel(painel_id: str):
    """Atualiza o painel com jogadores atuais"""
    fila = gerenciador.filas_ativas.get(painel_id)
    if not fila or not fila.get("msg_painel_id"):
        return

    texto = ""

    if fila["jogadores_normal"]:
        texto += "**⚪ Normal:**\n"
        for j in fila["jogadores_normal"]:
            texto += f"  {j.mention} - {fila['tamanho']}\n"
        texto += "\n"

    if fila["jogadores_full_ump"]:
        texto += "**🎯 Full Ump Xm8:**\n"
        for j in fila["jogadores_full_ump"]:
            texto += f"  {j.mention} - {fila['tamanho']}\n"
        texto += "\n"

    if fila["jogadores_mobilador"]:
        texto += "**🚀 Mobilador:**\n"
        for j in fila["jogadores_mobilador"]:
            texto += f"  {j.mention} - {fila['tamanho']}\n"

    if not texto:
        texto = "Nenhum jogador na fila."

    emoji_map = {
        "mobile": "📱",
        "emu": "💻",
        "misto": "🖥️"
    }
    emoji = emoji_map.get(fila["plataforma"], "🎮")

    embed = discord.Embed(
        title=f"{emoji} {fila['nome']}",
        color=COR_PRINCIPAL
    )
    embed.add_field(name="💰 Valor Partida", value=f"R$ {fila['valor']:.2f}", inline=False)
    embed.add_field(name="⚙️ Modo", value=f"{fila['tamanho']} {fila['plataforma'].capitalize()}", inline=False)
    embed.add_field(name="👥 Jogadores na fila", value=texto, inline=False)

    try:
        canal_aceitar = bot.get_channel(config.canal_aceitar)
        msg = await canal_aceitar.fetch_message(fila["msg_painel_id"])
        view = ViewEntrarFila(painel_id, fila["tamanho"], fila["plataforma"], fila["valor"])
        await msg.edit(embed=embed, view=view)
    except:
        pass

# ============================================
# VIEWS NO CANAL DA PARTIDA
# ============================================

class ViewPartidaCanal(ui.View):
    """View dentro do canal da partida"""
    def __init__(self, game_id: str):
        super().__init__(timeout=None)
        self.game_id = game_id

    @ui.button(label="Pedir Analista", style=discord.ButtonStyle.primary, emoji="🔍")
    async def btn_analista(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="📞 ANALISTA SOLICITADO",
            color=COR_AVISO
        )
        embed.add_field(name="👤 Solicitante", value=interaction.user.mention, inline=False)
        embed.add_field(name="🎮 Partida", value=f"`{self.game_id}`", inline=False)

        canal = interaction.channel
        await canal.send(embed=embed)
        await interaction.followup.send("✅ Analista solicitado!", ephemeral=True)

class ViewAceitarFila(ui.View):
    """View no canal de aceitar fila"""
    def __init__(self, game_id: str, canal_id: int):
        super().__init__(timeout=None)
        self.game_id = game_id
        self.canal_id = canal_id

    @ui.button(label="Aceitar Fila", style=discord.ButtonStyle.success, emoji="✅")
    async def btn_aceitar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id not in config.admin_ids:
            await interaction.followup.send("❌ Você não é um admin!", ephemeral=True)
            return

        partida = gerenciador.partidas.get(self.game_id)
        if not partida:
            await interaction.followup.send("❌ Partida não encontrada!", ephemeral=True)
            return

        # Registrar admin responsável
        gerenciador.admins_sala[self.game_id] = interaction.user.id
        partida["status"] = "confirmada"
        partida["admin"] = interaction.user.id

        # Adicionar admin ao canal
        canal = bot.get_channel(self.canal_id)
        await canal.set_permissions(interaction.user, view_channel=True, send_messages=True, manage_messages=True)

        # Notificar no canal
        embed_confirm = discord.Embed(
            title="✅ FILA CONFIRMADA!",
            color=COR_SUCESSO
        )
        embed_confirm.add_field(name="👮 Admin Responsável", value=interaction.user.mention, inline=False)
        embed_confirm.add_field(name="🆔 Partida", value=f"`{self.game_id}`", inline=False)
        embed_confirm.set_footer(text="Admin pode gerenciar a sala agora!")

        await canal.send(embed=embed_confirm)

        # Log
        partida_info = gerenciador.partidas[self.game_id]
        time1 = " ".join([j.mention for j in partida_info["time1"]])
        time2 = " ".join([j.mention for j in partida_info["time2"]])

        embed_log = discord.Embed(
            title="✅ FILA ACEITA POR ADMIN",
            color=COR_SUCESSO
        )
        embed_log.add_field(name="👮 Admin", value=interaction.user.mention, inline=False)
        embed_log.add_field(name="🆔 ID Partida", value=f"`{self.game_id}`", inline=False)
        embed_log.add_field(name="👥 TIME 1", value=time1, inline=False)
        embed_log.add_field(name="👥 TIME 2", value=time2, inline=False)
        embed_log.add_field(name="⏰ Horário", value=f"<t:{int(datetime.now().timestamp())}:T>", inline=False)

        canal_log = bot.get_channel(config.canal_log)
        await canal_log.send(embed=embed_log)

        await interaction.followup.send("✅ Fila aceita com sucesso!", ephemeral=True)

    @ui.button(label="Cancelar Fila", style=discord.ButtonStyle.danger, emoji="❌")
    async def btn_cancelar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id not in config.admin_ids:
            await interaction.followup.send("❌ Você não é um admin!", ephemeral=True)
            return

        partida = gerenciador.partidas.get(self.game_id)
        if not partida:
            await interaction.followup.send("❌ Partida não encontrada!", ephemeral=True)
            return

        partida["status"] = "cancelada"

        # Notificar no canal
        canal = bot.get_channel(self.canal_id)
        embed_cancel = discord.Embed(
            title="❌ FILA CANCELADA",
            color=COR_DANGER
        )
        embed_cancel.add_field(name="👮 Cancelado por", value=interaction.user.mention, inline=False)
        embed_cancel.add_field(name="Motivo", value="Cancelado pelo admin", inline=False)

        await canal.send(embed=embed_cancel)

        # Deletar canal depois de 5 segundos
        await asyncio.sleep(5)
        try:
            await canal.delete(reason="Fila cancelada")
        except:
            pass

        # Log
        embed_log = discord.Embed(
            title="❌ FILA CANCELADA POR ADMIN",
            color=COR_DANGER
        )
        embed_log.add_field(name="👮 Admin", value=interaction.user.mention, inline=False)
        embed_log.add_field(name="🆔 ID Partida", value=f"`{self.game_id}`", inline=False)

        canal_log = bot.get_channel(config.canal_log)
        await canal_log.send(embed=embed_log)

        await interaction.followup.send("✅ Fila cancelada!", ephemeral=True)

# ============================================
# COMANDO HELP
# ============================================

@bot.tree.command(name="help", description="❓ Ver ajuda")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="❓ AJUDA - COMANDOS",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="/config_bot",
        value="Configurar canais de log e aceitar",
        inline=False
    )

    embed.add_field(
        name="/config_categoria",
        value="Configurar categoria para um tamanho",
        inline=False
    )

    embed.add_field(
        name="/admin_add",
        value="Adicionar um admin",
        inline=False
    )

    embed.add_field(
        name="/genfila",
        value="Criar um painel de fila",
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================
# EXECUTAR BOT
# ============================================

def main():
    TOKEN = "SEU_TOKEN_AQUI"

    print("=" * 70)
    print("🎮 BOT APOSTAS FREE FIRE - SISTEMA COMPLETO")
    print("=" * 70)
    print("✅ /config_bot - Configurar canais")
    print("✅ /config_categoria - Configurar categorias")
    print("✅ /admin_add - Adicionar admins")
    print("✅ /genfila - Criar filas customizadas")
    print("✅ Canais privados por partida")
    print("✅ Sistema de confirmação com admins")
    print("✅ Logs automáticos")
    print("=" * 70)

    bot.run(TOKEN)

if __name__ == "__main__":
    main()
