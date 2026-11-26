import re
import csv
import io
import discord
from discord.ext import commands

# 1. Intents（インテント）の設定
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- 設定値 ---
TARGET_GUILD_ID = 1066275512198103180      # サーバーID
COMMAND_CHANNEL_ID = 1075740818213699595 # ディスボード操作用（コマンド実行用）
TARGET_CHANNEL_ID = 1066283854748463104  # id置き場チャンネル（スキャン対象）
ROLE_WRITTEN_ID = 1067002006063042582    # 「ID書き込み済」ロールID

# 3～15文字の半角英数字、アンダースコア(_)、ハイフン(-)、ドット(.)の正規表現
ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{3,15}$")


@bot.event
async def on_ready():
    print(f"ログインしました: {bot.user} (ID: {bot.user.id})")


# ==========================================
# 1. デモ実行（テスト・シミュレーション用）コマンド
# ==========================================
@bot.command(name="test_scan")
@commands.has_permissions(administrator=True)
async def test_scan(ctx):
    if ctx.guild.id != TARGET_GUILD_ID or ctx.channel.id != COMMAND_CHANNEL_ID:
        await ctx.send("❌ このチャンネルでは実行できません。運営会議チャンネルで実行してください。")
        return

    await ctx.send("🔍 **【デモ実行】** id置き場の履歴スキャン（シミュレーション）を開始します...\n※今回はロールの剥奪は行いません。")

    channel = ctx.guild.get_channel(TARGET_CHANNEL_ID)
    role_written = ctx.guild.get_role(ROLE_WRITTEN_ID)

    if not channel or not role_written:
        await ctx.send("❌ チャンネルまたは「ID書き込み済」ロールが見つかりませんでした。")
        return

    # 履歴から有効なIDのユーザーIDを収集
    valid_user_ids = set()
    async for message in channel.history(limit=None):
        if message.author.bot:
            continue
        content = message.content.strip()
        if ID_REGEX.match(content):
            valid_user_ids.add(message.author.id)

    # 剥奪対象になるメンバーを検出（※ロール変更はしない）
    target_records = []
    for member in role_written.members:
        if member.id not in valid_user_ids:
            target_records.append([member.id, member.name, member.display_name])

    # 結果のプレビューをCSVで送信
    if target_records:
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["User ID", "Username", "Display Name"])
        writer.writerows(target_records)

        file_bytes = io.BytesIO(csv_buffer.getvalue().encode("utf-8-sig"))
        discord_file = discord.File(fp=file_bytes, filename="test_scan_preview.csv")

        await ctx.send(
            f"🧪 **【デモ実行結果】**\n"
            f"実際に実行した場合、**{len(target_records)}名** のユーザーから「ID書き込み済」ロールが剥奪されます。\n"
            f"（※今回はデモ実行のため、ロールは一切変更されていません）\n"
            f"対象者プレビューのCSVファイルを添付します。",
            file=discord_file
        )
    else:
        await ctx.send("🧪 **【デモ実行結果】**\n条件に該当する（ロール剥奪対象となる）ユーザービリティはありませんでした。全員有効な書き込みがあります。")


# ==========================================
# 2. 本番実行（実際にロールを剥奪する）コマンド
# ==========================================
@bot.command(name="scan_id")
@commands.has_permissions(administrator=True)  # 管理者のみ実行可能
async def scan_id(ctx):
    if ctx.guild.id != TARGET_GUILD_ID or ctx.channel.id != COMMAND_CHANNEL_ID:
        await ctx.send("❌ このチャンネルでは実行できません。運営会議チャンネルで実行してください。")
        return

    await ctx.send("🔍 **【本番実行】** id置き場の履歴スキャンを開始します（ロール回収を行います）...")

    channel = ctx.guild.get_channel(TARGET_CHANNEL_ID)
    role_written = ctx.guild.get_role(ROLE_WRITTEN_ID)

    if not channel or not role_written:
        await ctx.send("❌ チャンネルまたは「ID書き込み済」ロールが見つかりませんでした。")
        return

    valid_user_ids = set()
    async for message in channel.history(limit=None):
        if message.author.bot:
            continue
        content = message.content.strip()
        if ID_REGEX.match(content):
            valid_user_ids.add(message.author.id)

    removed_records = []
    for member in role_written.members:
        if member.id not in valid_user_ids:
            try:
                # 実際にロールを剥がす
                await member.remove_roles(role_written, reason="ID置き場に有効な書き込みがないためスキャンにより削除")
                removed_records.append([member.id, member.name, member.display_name])
            except discord.Forbidden:
                print(f"権限不足で {member.display_name} のロールを変更できませんでした。")

    if removed_records:
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["User ID", "Username", "Display Name"])
        writer.writerows(removed_records)

        file_bytes = io.BytesIO(csv_buffer.getvalue().encode("utf-8-sig"))
        discord_file = discord.File(fp=file_bytes, filename="scan_removed_users.csv")

        await ctx.send(
            f"✅ **【本番実行完了】**\n"
            f"有効な書き込み履歴がない **{len(removed_records)}名** のユーザーから「ID書き込み済」ロールを回収しました。\n"
            f"処理結果一覧のCSVファイルを添付します。",
            file=discord_file
        )
    else:
        await ctx.send("✅ **【本番実行完了】** 条件に該当するユーザーはいませんでした。")


# Botの起動トークン
bot.run("MTU2NjA2MjEwOTcyMzE5NzUyMA.GsjidL.O7Vrl3UWwLdg6rjGuTkyR9CNhrg_jnT2EjuzQY")