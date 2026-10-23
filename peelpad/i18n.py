"""Peelpad in your language: English, Arabic, Spanish, Japanese or Chinese.

`tr(text)` looks the English text up and gives it back in the chosen language
(English when a line has no translation yet). The language follows Windows
unless one is picked in Settings > General. Arabic lays the windows out right
to left.
"""

from __future__ import annotations

from datetime import date

LANGS = [("auto", "Auto (Windows)"), ("en", "English"), ("ar", "العربية"), ("es", "Español"), ("ja", "日本語"),
         ("zh", "中文")]
ORDER = ("ar", "es", "ja", "zh")
LOCALES = {"en": "en_GB", "ar": "ar_MA", "es": "es_ES", "ja": "ja_JP", "zh": "zh_CN"}
LANG = "en"

# English: (Arabic, Spanish, Japanese, Chinese)
T: dict[str, tuple[str, str, str, str]] = {
    # ---- the pad, notes, tray
    "Write a task…": ("اكتب مهمة…", "Escribe una tarea…", "タスクを書く…", "写一个任务…"),
    "Check it off · right-click: plain line / task": (
        "أشّر عليها · زر الفأرة الأيمن: سطر عادي / مهمة", "Márcala · clic derecho: línea normal / tarea",
        "チェックする · 右クリック: ただの行 / タスク", "勾选 · 右键: 普通行 / 任务"),
    "Resize: drag the handles, then press ✓": (
        "تغيير الحجم: اسحب المقابض ثم اضغط ✓", "Cambiar tamaño: arrastra las asas y pulsa ✓",
        "サイズ変更: ハンドルをドラッグして ✓ を押す", "调整大小: 拖动手柄, 然后按 ✓"),
    "Keep this size": ("احتفظ بهذا الحجم", "Mantener este tamaño", "このサイズにする", "保持这个大小"),
    "Done: crumple it": ("تم: كوّرها", "Hecho: arrúgala", "完了: くしゃっと丸める", "完成: 揉成一团"),
    "Next colour": ("اللون التالي", "Siguiente color", "次の色", "下一个颜色"),
    "Throw it away": ("ارمها", "Tírala", "捨てる", "扔掉"),
    "Click again to throw it away": ("اضغط مرة ثانية لرميها", "Pulsa otra vez para tirarla",
                                     "もう一度押すと捨てます", "再点一次扔掉"),
    "Settings, stats and history": ("الإعدادات والإحصائيات والسجل", "Ajustes, estadísticas e historial",
                                    "設定・統計・履歴", "设置、统计和历史"),
    "Minimise to the taskbar": ("تصغير إلى شريط المهام", "Minimizar a la barra de tareas",
                                "タスクバーに最小化", "最小化到任务栏"),
    "Write something on it first": ("اكتب عليها شيئاً أولاً", "Escribe algo primero", "先に何か書いてください",
                                    "先在上面写点东西"),
    "Settings && stats": ("الإعدادات والإحصائيات", "Ajustes y estadísticas", "設定と統計", "设置和统计"),
    "Keep the pad on top": ("الدفتر فوق كل النوافذ", "Bloc siempre encima", "パッドを常に手前に", "便签本置顶"),
    "Hide the pad": ("إخفاء الدفتر", "Ocultar el bloc", "パッドを隠す", "隐藏便签本"),
    "Quit Peelpad": ("إغلاق Peelpad", "Salir de Peelpad", "Peelpad を終了", "退出 Peelpad"),
    "Show the pad": ("إظهار الدفتر", "Mostrar el bloc", "パッドを表示", "显示便签本"),
    "Minimise": ("تصغير", "Minimizar", "最小化", "最小化"),
    "Close": ("إغلاق", "Cerrar", "閉じる", "关闭"),
    # ---- settings: tabs
    "Stats": ("الإحصائيات", "Estadísticas", "統計", "统计"),
    "History": ("السجل", "Historial", "履歴", "历史"),
    "Look": ("المظهر", "Aspecto", "見た目", "外观"),
    "Writing": ("الكتابة", "Escritura", "文字", "文字"),
    "General": ("عام", "General", "一般", "常规"),
    # ---- stats
    "days you wrote notes": ("أيام كتبت فيها ملاحظات", "días que escribiste notas", "メモを書いた日", "写过便签的天数"),
    "days you checked off everything you wrote": (
        "أيام أنهيت فيها كل ما كتبت", "días que completaste todo lo que escribiste",
        "書いたことを全部終えた日", "完成了所写全部任务的天数"),
    "day streak right now": ("أيام متتالية الآن", "días seguidos ahora", "今の連続日数", "当前连续天数"),
    "best streak": ("أطول سلسلة", "mejor racha", "最長連続", "最长连续"),
    "notes finished and crumpled": ("ملاحظات أُنجزت وكُوّرت", "notas terminadas y arrugadas",
                                    "完了して丸めたメモ", "完成并揉掉的便签"),
    "tasks checked": ("مهام مؤشّرة", "tareas marcadas", "チェックしたタスク", "已勾选的任务"),
    "Last 18 weeks": ("آخر 18 أسبوعاً", "Últimas 18 semanas", "直近18週間", "最近18周"),
    "wrote something": ("كتبت شيئاً", "escribiste algo", "何か書いた", "写了东西"),
    "checked off everything": ("أنهيت كل شيء", "completaste todo", "全部終えた", "全部完成"),
    "today": ("اليوم", "hoy", "今日", "今天"),
    "{p}% of all your tasks are done · {n} notes pinned now": (
        "{p}% من كل مهامك منجزة · {n} ملاحظات مثبّتة الآن", "{p}% de tus tareas hechas · {n} notas fijadas ahora",
        "全タスクの {p}% 完了 · 今ピン留め中のメモ {n} 枚", "已完成全部任务的 {p}% · 当前固定 {n} 张便签"),
    # ---- history
    "Today": ("اليوم", "Hoy", "今日", "今天"),
    "Delete ticked": ("احذف المؤشَّر", "Borrar marcadas", "チェックしたものを削除", "删除勾选项"),
    "Tick tasks in the list, then delete them from History": (
        "أشّر على مهام في القائمة ثم احذفها من السجل", "Marca tareas en la lista y bórralas del historial",
        "リストでタスクにチェックして履歴から削除", "在列表中勾选任务, 然后从历史中删除"),
    "Delete this day": ("احذف هذا اليوم", "Borrar este día", "この日を削除", "删除这一天"),
    "Delete everything…": ("احذف كل شيء…", "Borrar todo…", "すべて削除…", "全部删除…"),
    "Every finished or thrown-away note. Notes still pinned stay.": (
        "كل ملاحظة منجزة أو مرمية. الملاحظات المثبّتة تبقى.", "Todas las notas terminadas o tiradas. Las fijadas se quedan.",
        "完了または捨てたメモすべて。ピン留め中のメモは残ります。", "所有已完成或已扔掉的便签。仍固定的便签会保留。"),
    "Nothing written or checked off this day.": (
        "لم يُكتب أو يُنجز شيء في هذا اليوم.", "Nada escrito ni completado este día.",
        "この日は何も書いていません。", "这一天没有写也没有完成任何事。"),
    "{n} checked off": ("{n} منجزة", "{n} completadas", "{n} 件完了", "完成 {n} 项"),
    "{n} written": ("{n} مكتوبة", "{n} escritas", "{n} 件書いた", "写了 {n} 项"),
    "on a pinned note": ("على ملاحظة مثبّتة", "en una nota fijada", "ピン留め中のメモ", "在固定的便签上"),
    "This task is on a note that is still pinned. Finish or throw the note away first.": (
        "هذه المهمة على ملاحظة ما زالت مثبّتة. أنهِ الملاحظة أو ارمها أولاً.",
        "Esta tarea está en una nota fijada. Termínala o tírala primero.",
        "このタスクはピン留め中のメモにあります。先にメモを完了するか捨ててください。",
        "这个任务在仍固定的便签上。请先完成或扔掉那张便签。"),
    "{n} of them are on notes still pinned, so they stay. Finish or throw those notes away first.": (
        "{n} منها على ملاحظات ما زالت مثبّتة، فتبقى. أنهِ تلك الملاحظات أو ارمها أولاً.",
        "{n} están en notas fijadas, así que se quedan. Termina o tira esas notas primero.",
        "{n} 件はピン留め中のメモにあるので残ります。先にそのメモを完了するか捨ててください。",
        "其中 {n} 项在仍固定的便签上, 所以保留。请先完成或扔掉那些便签。"),
    "Delete everything from {day} in History?": (
        "حذف كل شيء من {day} في السجل؟", "¿Borrar todo lo del {day} del historial?",
        "履歴から {day} の分をすべて削除しますか?", "从历史中删除 {day} 的全部内容?"),
    "Delete all of History: every finished or thrown-away note, and the stats that come from them? Notes still pinned stay.": (
        "حذف السجل كله: كل ملاحظة منجزة أو مرمية والإحصائيات المبنية عليها؟ الملاحظات المثبّتة تبقى.",
        "¿Borrar todo el historial: cada nota terminada o tirada y sus estadísticas? Las notas fijadas se quedan.",
        "履歴をすべて削除しますか? 完了・捨てたメモとその統計が消えます。ピン留め中のメモは残ります。",
        "删除全部历史: 所有已完成或扔掉的便签及其统计? 仍固定的便签会保留。"),
    # ---- look
    "Note look": ("شكل الملاحظة", "Aspecto de la nota", "メモの見た目", "便签外观"),
    "Retro LED clock colour": ("لون ساعة LED القديمة", "Color del reloj LED retro", "レトロLED時計の色", "复古LED时钟颜色"),
    "Weather (for the Weather look)": ("الطقس (لشكل الطقس)", "Tiempo (para el aspecto Tiempo)",
                                       "天気(「天気」の見た目用)", "天气(用于天气外观)"),
    "Your city, e.g. Casablanca": ("مدينتك، مثلاً الدار البيضاء", "Tu ciudad, p. ej. Madrid", "都市名 (例: Tokyo)",
                                   "你的城市, 例如 Beijing"),
    "Set": ("تعيين", "Fijar", "設定", "设定"),
    "Live follows the sky over your city and changes by itself. The others show that weather so you can see it. "
    "Only the city goes to Open-Meteo (open-meteo.com), every 20 minutes while you use this look; your notes never "
    "leave your PC.": (
        "«مباشر» يتبع سماء مدينتك ويتغير وحده. والبقية تعرض ذلك الطقس لتراه. يُرسل اسم المدينة فقط إلى Open-Meteo "
        "(open-meteo.com) كل 20 دقيقة ما دمت تستخدم هذا الشكل؛ ملاحظاتك لا تغادر جهازك أبداً.",
        "En vivo sigue el cielo de tu ciudad y cambia solo. Los demás muestran ese tiempo para que lo veas. Solo la "
        "ciudad va a Open-Meteo (open-meteo.com), cada 20 minutos mientras uses este aspecto; tus notas nunca salen de tu PC.",
        "「ライブ」はあなたの街の空に合わせて自動で変わります。ほかは各天気のプレビューです。Open-Meteo "
        "(open-meteo.com) に送るのは都市名だけで、この見た目を使っている間の20分ごとです。メモがPCの外に出ることはありません。",
        "“实时”跟随你所在城市的天空自动变化。其他选项用于预览各种天气。只有城市名会发送到 Open-Meteo "
        "(open-meteo.com), 使用此外观时每20分钟一次; 你的便签从不离开你的电脑。"),
    "Text box": ("مربع الكتابة", "Caja de texto", "テキスト枠", "文字框"),
    "Where the writing goes on this look. Drag the box to move it, drag its corners to make it bigger or smaller. "
    "Peelpad finds the calm middle of your own pictures by itself.": (
        "مكان الكتابة في هذا الشكل. اسحب المربع لتحريكه واسحب زواياه لتكبيره أو تصغيره. يجد Peelpad المنطقة الهادئة "
        "في وسط صورك بنفسه.",
        "Dónde va el texto en este aspecto. Arrastra la caja para moverla y sus esquinas para cambiar su tamaño. "
        "Peelpad encuentra solo el centro tranquilo de tus imágenes.",
        "この見た目で文字を書く場所です。枠をドラッグで移動、角をドラッグで拡大縮小。自分の画像では静かな中央部分を"
        "Peelpad が自動で見つけます。",
        "这个外观上写字的位置。拖动方框来移动, 拖动角来放大或缩小。Peelpad 会自动找到你图片中安静的中间区域。"),
    "Auto": ("تلقائي", "Auto", "自動", "自动"),
    "Put the text box back where Peelpad would put it": (
        "أرجع مربع الكتابة إلى حيث يضعه Peelpad", "Devolver la caja a donde la pondría Peelpad",
        "テキスト枠を Peelpad の標準位置に戻す", "把文字框放回 Peelpad 的默认位置"),
    "Your colours": ("ألوانك", "Tus colores", "自分の色", "你的颜色"),
    "Paper colour…": ("لون الورقة…", "Color del papel…", "紙の色…", "纸张颜色…"),
    "Ink colour…": ("لون الحبر…", "Color de la tinta…", "インクの色…", "墨水颜色…"),
    "Paper colour": ("لون الورقة", "Color del papel", "紙の色", "纸张颜色"),
    "Glowing ink": ("حبر مضيء", "Tinta brillante", "光るインク", "发光墨水"),
    "Size": ("الحجم", "Tamaño", "サイズ", "大小"),
    "Pad sheets": ("أوراق الدفتر", "Hojas del bloc", "パッドの紙", "便签纸"),
    "Pinned notes can be any size: press ↕ under a note, drag its handles (hold Shift to keep its shape), then press "
    "✓. Or hold Ctrl and turn the mouse wheel over it. Ctrl + wheel over the pad changes the size of its sheets.": (
        "الملاحظات المثبّتة بأي حجم: اضغط ↕ تحت الملاحظة واسحب مقابضها (Shift يحافظ على الشكل) ثم اضغط ✓. أو اضغط Ctrl "
        "وأدر عجلة الفأرة فوقها. Ctrl مع العجلة فوق الدفتر يغير حجم أوراقه.",
        "Las notas fijadas pueden tener cualquier tamaño: pulsa ↕ debajo, arrastra las asas (Mayús mantiene la forma) "
        "y pulsa ✓. O mantén Ctrl y gira la rueda encima. Ctrl + rueda sobre el bloc cambia el tamaño de sus hojas.",
        "ピン留めしたメモは自由なサイズに: 下の ↕ を押してハンドルをドラッグ (Shift で形を保つ) し、✓ を押します。"
        "または Ctrl を押しながらマウスホイール。パッドの上で Ctrl + ホイールで紙のサイズが変わります。",
        "固定的便签可以是任意大小: 按下方的 ↕, 拖动手柄 (按住 Shift 保持形状), 然后按 ✓。或按住 Ctrl 在上面滚动鼠标滚轮。"
        "在便签本上 Ctrl + 滚轮可改变纸张大小。"),
    "Your own skin": ("شكلك الخاص", "Tu propio aspecto", "自分のスキン", "你自己的皮肤"),
    "Upload your own skin…": ("ارفع شكلك الخاص…", "Subir tu propio aspecto…", "スキンをアップロード…", "上传你的皮肤…"),
    "Save the template PNG…": ("احفظ قالب PNG…", "Guardar la plantilla PNG…", "テンプレートPNGを保存…", "保存模板 PNG…"),
    "Delete all my uploaded skins…": ("احذف كل الأشكال التي رفعتها…", "Borrar todos mis aspectos subidos…",
                                      "アップロードしたスキンをすべて削除…", "删除我上传的所有皮肤…"),
    "Only the pictures you uploaded; Peelpad's own looks stay": (
        "فقط الصور التي رفعتها؛ أشكال Peelpad تبقى", "Solo las imágenes que subiste; los aspectos de Peelpad se quedan",
        "アップロードした画像だけ。Peelpad の見た目は残ります", "只删除你上传的图片; Peelpad 自带的外观保留"),
    "Copy a prompt for an animated skin": ("انسخ وصفاً لتصميم شكل متحرك", "Copiar un prompt para un aspecto animado",
                                           "アニメスキン用のプロンプトをコピー", "复制动画皮肤的提示词"),
    "Paste it into an AI image or animation tool, or send it to an artist": (
        "الصقه في أداة ذكاء اصطناعي للصور أو الرسوم المتحركة، أو أرسله لمصمم",
        "Pégalo en una herramienta de IA de imagen o animación, o envíalo a un artista",
        "AI画像・アニメツールに貼り付けるか、デザイナーに送ってください", "粘贴到 AI 图像或动画工具中, 或发给设计师"),
    "Copied. Paste it into your AI tool and change the animation idea.": (
        "تم النسخ. الصقه في أداة الذكاء الاصطناعي وغيّر فكرة الحركة.",
        "Copiado. Pégalo en tu herramienta de IA y cambia la idea de la animación.",
        "コピーしました。AIツールに貼り付けて、アニメのアイデアを変えてください。", "已复制。粘贴到你的 AI 工具里, 并修改动画创意。"),
    "Choose your skin": ("اختر شكلك", "Elige tu aspecto", "スキンを選ぶ", "选择你的皮肤"),
    "Pictures, still or animated": ("صور، ثابتة أو متحركة", "Imágenes, fijas o animadas", "画像 (静止またはアニメ)",
                                    "图片 (静态或动画)"),
    "Save the skin template": ("احفظ قالب الشكل", "Guardar la plantilla", "スキンのテンプレートを保存", "保存皮肤模板"),
    "Your skin is on. A heads-up:": ("تم تطبيق شكلك. ملاحظة:", "Tu aspecto está puesto. Un aviso:",
                                     "スキンを適用しました。お知らせ:", "你的皮肤已应用。提示:"),
    "Delete this skin": ("احذف هذا الشكل", "Borrar este aspecto", "このスキンを削除", "删除这个皮肤"),
    "Delete this skin? Notes wearing it go back to neon.": (
        "حذف هذا الشكل؟ الملاحظات التي تستخدمه ترجع إلى النيون.", "¿Borrar este aspecto? Las notas que lo usan vuelven al neón.",
        "このスキンを削除しますか? 使っているメモはネオンに戻ります。", "删除这个皮肤? 使用它的便签会恢复为霓虹。"),
    "Delete all {n} skins you uploaded? Peelpad's own looks stay.": (
        "حذف كل الأشكال التي رفعتها ({n})؟ أشكال Peelpad تبقى.", "¿Borrar los {n} aspectos que subiste? Los de Peelpad se quedan.",
        "アップロードしたスキン {n} 個をすべて削除しますか? Peelpad の見た目は残ります。", "删除你上传的全部 {n} 个皮肤? Peelpad 自带的外观保留。"),
    "Your tasks here": ("مهامك هنا", "Tus tareas aquí", "ここにタスク", "你的任务在这里"),
    "Type your city and press Set.": ("اكتب مدينتك واضغط تعيين.", "Escribe tu ciudad y pulsa Fijar.",
                                      "都市名を入力して「設定」を押してください。", "输入你的城市, 然后按“设定”。"),
    "Clock colour": ("لون الساعة", "Color del reloj", "時計の色", "时钟颜色"),
    "{city}: {weather}{night} · checked {time}": (
        "{city}: {weather}{night} · آخر تحديث {time}", "{city}: {weather}{night} · comprobado a las {time}",
        "{city}: {weather}{night} · {time} 更新", "{city}: {weather}{night} · {time} 更新"),
    "{city}: the weather shows once the Weather look is in use.": (
        "{city}: يظهر الطقس عند استخدام شكل الطقس.", "{city}: el tiempo aparece al usar el aspecto Tiempo.",
        "{city}: 「天気」の見た目を使うと天気が表示されます。", "{city}: 使用天气外观时会显示天气。"),
    " (night)": (" (ليلاً)", " (noche)", " (夜)", " (夜间)"),
    "Looking for it…": ("جارٍ البحث…", "Buscando…", "検索中…", "正在查找…"),
    "Couldn't find that city. Try its English name.": (
        "لم أجد هذه المدينة. جرّب اسمها بالإنجليزية.", "No encontré esa ciudad. Prueba con su nombre en inglés.",
        "その都市が見つかりません。英語名で試してください。", "找不到这个城市。请试试它的英文名。"),
    "Couldn't reach the weather service (no internet?). Peelpad tries again later.": (
        "تعذّر الوصول إلى خدمة الطقس (لا يوجد إنترنت؟). سيحاول Peelpad لاحقاً.",
        "No se pudo contactar con el servicio del tiempo (¿sin internet?). Peelpad lo intentará más tarde.",
        "天気サービスに接続できません (インターネットなし?)。後でもう一度試します。", "无法连接天气服务 (没有网络?)。Peelpad 稍后会重试。"),
    "<b>Design your own skin</b> — scary, cute, anything:<br>"
    "• <b>Size:</b> {size} × {size} px (a square). Other sizes work too: new notes take your picture's shape, and "
    "anything from 300 px up stays sharp.<br>"
    "• <b>Format:</b> PNG. Transparent pixels are see-through on your desktop (and clicks go through them), so a skin "
    "can be any shape: a ghost, a cat, a torn page. JPG and WebP work without transparency.<br>"
    "• <b>Safe text area:</b> tasks are written inside {safe_w} × {safe_h} px: {side} px in from the left, right and "
    "bottom, and {glue} px down from the top. The top {glue} px is the glue band, where the pin sits and where you grab "
    "the note. Decorate it, but keep the text area calm so tasks stay readable.<br>"
    "• <b>Ink:</b> picked for you (dark on light pictures, light on dark), or set it in Writing.<br>"
    "• <b>Animated:</b> an animated GIF, APNG or WebP plays on every note, looping. Same size and text area; keep the "
    "moving parts around the edges.<br>"
    "Save the template, paint over it in any editor, upload it, and every note switches to it at once.": (
        "<b>صمّم شكلك الخاص</b> — مخيف، لطيف، أي شيء:<br>"
        "• <b>الحجم:</b> {size} × {size} بكسل (مربع). الأحجام الأخرى تعمل أيضاً: الملاحظات الجديدة تأخذ شكل صورتك، "
        "وأي شيء من 300 بكسل فأكثر يبقى حاداً.<br>"
        "• <b>الصيغة:</b> PNG. البكسلات الشفافة تُظهر سطح المكتب (والنقرات تمر عبرها)، فيمكن أن يكون الشكل أي هيئة: "
        "شبح، قطة، ورقة ممزقة. JPG وWebP تعمل بدون شفافية.<br>"
        "• <b>منطقة الكتابة الآمنة:</b> تُكتب المهام داخل {safe_w} × {safe_h} بكسل: {side} بكسل من اليسار واليمين "
        "والأسفل، و{glue} بكسل من الأعلى. أعلى {glue} بكسل هو شريط الصمغ، حيث الدبوس وحيث تمسك الملاحظة. زيّنه، "
        "لكن اجعل منطقة الكتابة هادئة لتبقى المهام مقروءة.<br>"
        "• <b>الحبر:</b> يُختار لك (داكن على الصور الفاتحة وفاتح على الداكنة)، أو اختره من الكتابة.<br>"
        "• <b>متحرك:</b> صورة GIF أو APNG أو WebP متحركة تعمل على كل ملاحظة بشكل متكرر. نفس الحجم ومنطقة الكتابة؛ "
        "اجعل الأجزاء المتحركة حول الأطراف.<br>"
        "احفظ القالب، ارسم فوقه في أي برنامج، ارفعه، وتتحول كل الملاحظات إليه فوراً.",
        "<b>Diseña tu propio aspecto</b>: de miedo, mono, lo que quieras:<br>"
        "• <b>Tamaño:</b> {size} × {size} px (un cuadrado). Otros tamaños también sirven: las notas nuevas toman la forma "
        "de tu imagen, y desde 300 px se ve nítido.<br>"
        "• <b>Formato:</b> PNG. Los píxeles transparentes dejan ver el escritorio (y los clics pasan a través), así que "
        "un aspecto puede tener cualquier forma: un fantasma, un gato, una página rota. JPG y WebP funcionan sin transparencia.<br>"
        "• <b>Zona segura para el texto:</b> las tareas se escriben dentro de {safe_w} × {safe_h} px: a {side} px de la "
        "izquierda, derecha y abajo, y a {glue} px de arriba. Los {glue} px de arriba son la banda de pegamento, donde va "
        "la chincheta y por donde agarras la nota. Decórala, pero deja tranquila la zona del texto para que se lea bien.<br>"
        "• <b>Tinta:</b> se elige sola (oscura en imágenes claras, clara en oscuras), o cámbiala en Escritura.<br>"
        "• <b>Animado:</b> un GIF, APNG o WebP animado se reproduce en bucle en cada nota. Mismo tamaño y zona de texto; "
        "deja las partes que se mueven en los bordes.<br>"
        "Guarda la plantilla, pinta encima en cualquier editor, súbela y todas las notas cambian al instante.",
        "<b>自分のスキンを作ろう</b> — 怖くても、かわいくても:<br>"
        "• <b>サイズ:</b> {size} × {size} px (正方形)。ほかのサイズも使えます: 新しいメモは画像の形になり、"
        "300 px 以上ならくっきり表示されます。<br>"
        "• <b>形式:</b> PNG。透明なピクセルはデスクトップが透けて見え (クリックも通り抜けます)、オバケ、ネコ、"
        "破れた紙など、どんな形にもできます。JPG と WebP は透明なしで使えます。<br>"
        "• <b>安全な文字エリア:</b> タスクは {safe_w} × {safe_h} px の中に書かれます: 左右と下から {side} px、"
        "上から {glue} px。上の {glue} px はのり部分で、ピンがあり、メモをつかむ場所です。飾ってもいいですが、"
        "文字エリアは読みやすく落ち着いたままにしてください。<br>"
        "• <b>インク:</b> 自動で選ばれます (明るい画像には濃い色、暗い画像には明るい色)。「文字」で変更もできます。<br>"
        "• <b>アニメ:</b> アニメ GIF、APNG、WebP はすべてのメモでループ再生されます。サイズと文字エリアは同じで、"
        "動く部分は縁に置いてください。<br>"
        "テンプレートを保存して好きなアプリで描き、アップロードすると、すべてのメモがすぐに変わります。",
        "<b>设计你自己的皮肤</b> — 吓人的、可爱的, 什么都行:<br>"
        "• <b>尺寸:</b> {size} × {size} 像素 (正方形)。其他尺寸也可以: 新便签会采用你图片的形状, 300 像素以上都很清晰。<br>"
        "• <b>格式:</b> PNG。透明像素会透出桌面 (点击也会穿过), 所以皮肤可以是任何形状: 幽灵、猫、撕破的纸。"
        "JPG 和 WebP 可用, 但没有透明。<br>"
        "• <b>安全文字区:</b> 任务写在 {safe_w} × {safe_h} 像素内: 距左、右、下 {side} 像素, 距顶部 {glue} 像素。"
        "顶部 {glue} 像素是胶带区, 放图钉, 也是你抓住便签的地方。可以装饰, 但请让文字区保持简洁, 方便阅读。<br>"
        "• <b>墨水:</b> 自动选择 (亮图用深色, 暗图用浅色), 也可以在“文字”里设置。<br>"
        "• <b>动画:</b> 动画 GIF、APNG 或 WebP 会在每张便签上循环播放。尺寸和文字区相同; 让动的部分留在边缘。<br>"
        "保存模板, 在任何编辑器里画, 上传后所有便签立即换上。"),
    # ---- writing
    "Font": ("الخط", "Fuente", "フォント", "字体"),
    "Handwriting (default)": ("خط اليد (افتراضي)", "Manuscrita (predeterminada)", "手書き (標準)", "手写体 (默认)"),
    "Arabic writing": ("الكتابة العربية", "Escritura árabe", "アラビア文字", "阿拉伯文字"),
    "Pen (Aref Ruqaa)": ("قلم (عارف رقعة)", "Pluma (Aref Ruqaa)", "ペン (Aref Ruqaa)", "钢笔 (Aref Ruqaa)"),
    "Same as the font above": ("نفس الخط أعلاه", "Igual que la fuente de arriba", "上のフォントと同じ", "与上面的字体相同"),
    "Text size": ("حجم النص", "Tamaño del texto", "文字サイズ", "文字大小"),
    "Ink colour": ("لون الحبر", "Color de la tinta", "インクの色", "墨水颜色"),
    "Auto writes in each look's own ink: dark on neon and white paper, blue on Midnight, and so on. Pick any colour "
    "with the last button.": (
        "«تلقائي» يكتب بحبر كل شكل: داكن على النيون والورق الأبيض، وأزرق على منتصف الليل، وهكذا. اختر أي لون بالزر الأخير.",
        "Auto escribe con la tinta de cada aspecto: oscura en neón y papel blanco, azul en Medianoche, etc. Elige "
        "cualquier color con el último botón.",
        "「自動」は見た目ごとのインクで書きます: ネオンや白い紙では濃い色、Midnight では青など。"
        "最後のボタンで好きな色を選べます。",
        "“自动”使用每种外观自己的墨水: 霓虹和白纸上是深色, 午夜上是蓝色, 等等。用最后一个按钮选择任意颜色。"),
    "Effect": ("التأثير", "Efecto", "エフェクト", "效果"),
    "Neon shines like a sign, Toon gets a cartoon outline, Pop a bold offset shadow, Gummy a candy shine, Prism a "
    "rainbow. The row you are typing in stays plain until you leave it.": (
        "نيون يلمع كاللافتة، كرتون بحدود كرتونية، بوب بظل بارز، جيلي بلمعة الحلوى، وموشور بألوان قوس قزح. "
        "السطر الذي تكتب فيه يبقى عادياً حتى تتركه.",
        "Neón brilla como un letrero, Toon lleva contorno de dibujo animado, Pop una sombra marcada, Gominola un brillo "
        "de caramelo y Prisma un arcoíris. La fila que escribes se ve normal hasta que la dejas.",
        "ネオンは看板のように光り、トゥーンは漫画風の縁取り、ポップは大胆な影、グミはキャンディのつや、プリズムは虹色。"
        "入力中の行は離れるまで普通に表示されます。",
        "霓虹像招牌一样发光, 卡通有卡通描边, 波普有醒目的投影, 软糖有糖果般的光泽, 棱镜是彩虹色。"
        "正在输入的行在离开前保持普通样式。"),
    "Solid": ("عادي", "Sólido", "ベタ", "纯色"),
    "Gradient": ("تدرّج", "Degradado", "グラデーション", "渐变"),
    "Neon": ("نيون", "Neón", "ネオン", "霓虹"),
    "Toon": ("كرتون", "Toon", "トゥーン", "卡通"),
    "Pop": ("بوب", "Pop", "ポップ", "波普"),
    "Gummy": ("جيلي", "Gominola", "グミ", "软糖"),
    "Prism": ("موشور", "Prisma", "プリズム", "棱镜"),
    "Pick any colour": ("اختر أي لون", "Elige cualquier color", "好きな色を選ぶ", "选择任意颜色"),
    "Your colour {c} (click to change)": ("لونك {c} (اضغط للتغيير)", "Tu color {c} (pulsa para cambiar)",
                                          "あなたの色 {c} (クリックで変更)", "你的颜色 {c} (点击更改)"),
    # ---- general
    "Keep the pad on top of other windows (pinned notes always are)": (
        "اجعل الدفتر فوق النوافذ الأخرى (الملاحظات المثبّتة دائماً فوقها)",
        "Mantener el bloc encima de otras ventanas (las notas fijadas siempre lo están)",
        "パッドをほかのウィンドウより手前に (ピン留めしたメモは常に手前)", "便签本置于其他窗口之上 (固定的便签总是置顶)"),
    "Crumple a note by itself when every task on it is checked": (
        "كوّر الملاحظة وأخفها تلقائياً عند إنجاز كل مهامها",
        "Arrugar la nota sola cuando todas sus tareas estén marcadas",
        "タスクを全部チェックしたらメモを自動で丸めて消す",
        "便签上的任务全部勾选后自动揉掉"),
    "Turned off, a finished note stays on your screen until you press ✓ (done) or ✕ (throw it away) under it.": (
        "عند إيقافه، تبقى الملاحظة المنجزة على شاشتك حتى تضغط ✓ (تم) أو ✕ (ارمها) تحتها.",
        "Si lo desactivas, una nota terminada se queda en pantalla hasta que pulses ✓ (hecho) o ✕ (tirar) debajo.",
        "オフにすると、完了したメモは下の ✓ (完了) か ✕ (捨てる) を押すまで画面に残ります。",
        "关闭后, 已完成的便签会留在屏幕上, 直到你按下方的 ✓ (完成) 或 ✕ (扔掉)。"),
    "Wind": ("الرياح", "Viento", "風", "风"),
    "Wind blows your pinned notes (glued at the top; they hold still under your mouse)": (
        "الرياح تحرك ملاحظاتك المثبّتة (ملصوقة من الأعلى؛ تثبت تحت الفأرة)",
        "El viento mueve tus notas fijadas (pegadas arriba; se quedan quietas bajo el ratón)",
        "風でピン留めしたメモが揺れます (上はのりで固定。マウスを乗せると止まります)",
        "风吹动你固定的便签 (顶部粘住; 鼠标放上去时静止)"),
    "Speed": ("السرعة", "Velocidad", "速さ", "速度"),
    "Moving notes": ("تحريك الملاحظات", "Mover notas", "メモを動かす", "移动便签"),
    "Drag a note by its paper, or double-click it: it follows your mouse without holding the button, and lands where "
    "you click.": (
        "اسحب الملاحظة من ورقتها، أو اضغط عليها مرتين: تتبع الفأرة دون إمساك الزر، وتستقر حيث تضغط.",
        "Arrastra una nota por el papel o haz doble clic: sigue al ratón sin mantener el botón y se queda donde hagas clic.",
        "メモの紙をドラッグするか、ダブルクリック: ボタンを押さなくてもマウスについてきて、クリックした所に置かれます。",
        "拖动便签的纸面, 或双击它: 不用按住按键它也会跟随鼠标, 并落在你点击的位置。"),
    "Start Peelpad when Windows starts": ("شغّل Peelpad مع بدء Windows", "Abrir Peelpad al iniciar Windows",
                                          "Windows 起動時に Peelpad を開く", "Windows 启动时打开 Peelpad"),
    "Open the data folder": ("افتح مجلد البيانات", "Abrir la carpeta de datos", "データフォルダーを開く", "打开数据文件夹"),
    "Language": ("اللغة", "Idioma", "言語", "语言"),
    "Auto (Windows)": ("تلقائي (Windows)", "Auto (Windows)", "自動 (Windows)", "自动 (Windows)"),
    "<b>How it works</b><br>"
    "• Write on the pad's top sheet. <b>Enter</b> adds a task, <b>Backspace</b> on an empty one removes it.<br>"
    "• Grab the paper (anywhere that isn't writing) and pull: drag in over the sheet to curl it back, or pull it away to "
    "lift it, until it tears off. Drop it anywhere: it stays pinned on top.<br>"
    "• <b>Ctrl+Enter</b> peels the sheet off for you.<br>"
    "• Right-click a check box to make that row a plain line.<br>"
    "• Drag a pinned note by its paper: it swings like a real sheet. To resize it press ↕ under it, drag the handles, "
    "then ✓. Or Ctrl + mouse wheel.<br>"
    "• Check off every task and the note crumples away. ✓ finishes it by hand, ✕ throws it away.<br>"
    "• – minimises the pad to the taskbar. Peelpad also lives in the tray: right-click it to quit.<br>"
    "• Everything you write stays on this PC only, in the data folder above. The only thing Peelpad ever sends is your "
    "city, to Open-Meteo, and only while you use the Weather look.": (
        "<b>طريقة الاستخدام</b><br>"
        "• اكتب على الورقة العليا في الدفتر. <b>Enter</b> يضيف مهمة، و<b>Backspace</b> على مهمة فارغة يحذفها.<br>"
        "• امسك الورقة (في أي مكان ليس فيه كتابة) واسحب: اسحب فوق الورقة لتلتف، أو بعيداً عنها لترفعها، حتى تنفصل. "
        "ضعها في أي مكان: تبقى مثبّتة فوق كل شيء.<br>"
        "• <b>Ctrl+Enter</b> ينزع الورقة لك.<br>"
        "• زر الفأرة الأيمن على مربع التأشير يجعل السطر سطراً عادياً.<br>"
        "• اسحب الملاحظة المثبّتة من ورقتها: تتمايل كورقة حقيقية. لتغيير حجمها اضغط ↕ تحتها، اسحب المقابض، ثم ✓. "
        "أو Ctrl مع عجلة الفأرة.<br>"
        "• أنهِ كل المهام فتتكوّر الملاحظة وتختفي. ✓ ينهيها يدوياً، و✕ يرميها.<br>"
        "• – يصغّر الدفتر إلى شريط المهام. Peelpad موجود أيضاً في منطقة الإشعارات: اضغط عليه بالزر الأيمن للإغلاق.<br>"
        "• كل ما تكتبه يبقى على هذا الجهاز فقط، في مجلد البيانات أعلاه. الشيء الوحيد الذي يرسله Peelpad هو اسم مدينتك "
        "إلى Open-Meteo، وفقط عند استخدام شكل الطقس.",
        "<b>Cómo funciona</b><br>"
        "• Escribe en la hoja de arriba del bloc. <b>Intro</b> añade una tarea, <b>Retroceso</b> en una vacía la quita.<br>"
        "• Agarra el papel (donde no haya texto) y tira: arrastra por encima de la hoja para enrollarla, o aléjala para "
        "levantarla, hasta que se despegue. Suéltala donde quieras: se queda fijada encima.<br>"
        "• <b>Ctrl+Intro</b> despega la hoja por ti.<br>"
        "• Clic derecho en una casilla convierte esa fila en una línea normal.<br>"
        "• Arrastra una nota fijada por el papel: se balancea como una hoja de verdad. Para cambiar su tamaño pulsa ↕ "
        "debajo, arrastra las asas y pulsa ✓. O Ctrl + rueda del ratón.<br>"
        "• Marca todas las tareas y la nota se arruga y desaparece. ✓ la termina a mano, ✕ la tira.<br>"
        "• – minimiza el bloc a la barra de tareas. Peelpad también vive en la bandeja: clic derecho para salir.<br>"
        "• Todo lo que escribes se queda solo en este PC, en la carpeta de datos de arriba. Lo único que Peelpad envía "
        "es tu ciudad, a Open-Meteo, y solo mientras usas el aspecto Tiempo.",
        "<b>使い方</b><br>"
        "• パッドの一番上の紙に書きます。<b>Enter</b> でタスク追加、空の行で <b>Backspace</b> を押すと削除。<br>"
        "• 紙 (文字のない所) をつかんで引っ張ります: 紙の上に引くとめくれ、外に引くと持ち上がり、やがてはがれます。"
        "好きな所に置くと、手前にピン留めされます。<br>"
        "• <b>Ctrl+Enter</b> で自動ではがせます。<br>"
        "• チェックボックスを右クリックすると、その行はただの行になります。<br>"
        "• ピン留めしたメモは紙をドラッグ: 本物の紙のように揺れます。サイズ変更は下の ↕ を押してハンドルをドラッグし ✓。"
        "または Ctrl + マウスホイール。<br>"
        "• タスクを全部チェックするとメモはくしゃっと丸まって消えます。✓ で手動完了、✕ で捨てます。<br>"
        "• – でパッドをタスクバーに最小化。Peelpad は通知領域にもいます: 右クリックで終了。<br>"
        "• 書いた内容はこのPCの上のデータフォルダーにだけ保存されます。Peelpad が送るのは、天気の見た目を使っている間の"
        "都市名 (Open-Meteo へ) だけです。",
        "<b>使用方法</b><br>"
        "• 在便签本最上面的纸上写字。<b>Enter</b> 添加任务, 在空任务上按 <b>Backspace</b> 删除。<br>"
        "• 抓住纸 (没有文字的地方) 并拉: 往纸内拖会卷起, 往外拉会掀起, 直到撕下。放在任何地方: 它会固定在最上层。<br>"
        "• <b>Ctrl+Enter</b> 自动帮你撕下这张纸。<br>"
        "• 右键点击复选框, 把这一行变成普通行。<br>"
        "• 拖动固定便签的纸面: 它会像真纸一样摆动。要调整大小, 按下方的 ↕, 拖动手柄, 然后按 ✓。或 Ctrl + 鼠标滚轮。<br>"
        "• 勾选全部任务, 便签就会揉成一团消失。✓ 手动完成, ✕ 扔掉。<br>"
        "• – 把便签本最小化到任务栏。Peelpad 也在系统托盘里: 右键点击可退出。<br>"
        "• 你写的所有内容只保存在这台电脑上方的数据文件夹里。Peelpad 唯一会发送的是你的城市名 (发给 Open-Meteo), "
        "而且只在使用天气外观时。"),
    # ---- looks
    "Neon (a new colour each sheet)": ("نيون (لون جديد لكل ورقة)", "Neón (un color nuevo por hoja)",
                                       "ネオン (1枚ごとに新しい色)", "霓虹 (每张换一种颜色)"),
    "Lemon": ("ليموني", "Limón", "レモン", "柠檬"),
    "Mango": ("مانجو", "Mango", "マンゴー", "芒果"),
    "Bubblegum": ("علكة", "Chicle", "バブルガム", "泡泡糖"),
    "Lime": ("ليمون أخضر", "Lima", "ライム", "青柠"),
    "Midnight: black paper, glowing blue ink": ("منتصف الليل: ورق أسود وحبر أزرق مضيء",
                                                "Medianoche: papel negro, tinta azul brillante",
                                                "Midnight: 黒い紙に光る青インク", "午夜: 黑纸, 发光蓝墨水"),
    "Neon night: black paper, glowing pink ink": ("ليلة نيون: ورق أسود وحبر وردي مضيء",
                                                  "Noche neón: papel negro, tinta rosa brillante",
                                                  "ネオンナイト: 黒い紙に光るピンクインク", "霓虹之夜: 黑纸, 发光粉墨水"),
    "Toxic: black paper, glowing green ink": ("سام: ورق أسود وحبر أخضر مضيء", "Tóxico: papel negro, tinta verde brillante",
                                              "トキシック: 黒い紙に光る緑インク", "毒性: 黑纸, 发光绿墨水"),
    "Paper white": ("ورق أبيض", "Papel blanco", "白い紙", "白纸"),
    "Kraft": ("ورق كرافت", "Kraft", "クラフト紙", "牛皮纸"),
    "Skull parade (animated)": ("موكب الجماجم (متحرك)", "Desfile de calaveras (animado)", "ガイコツのパレード (アニメ)",
                                "骷髅游行 (动画)"),
    "Apple worm (animated)": ("دودة التفاح (متحرك)", "Gusano manzanero (animado)", "リンゴいもむし (アニメ)",
                              "苹果虫 (动画)"),
    "Retro LED clock (animated)": ("ساعة LED قديمة (متحرك)", "Reloj LED retro (animado)", "レトロLED時計 (アニメ)",
                                   "复古LED时钟 (动画)"),
    "Aquarium (animated)": ("حوض أسماك (متحرك)", "Acuario (animado)", "水族館 (アニメ)", "水族箱 (动画)"),
    "Night sky (animated)": ("سماء الليل (متحرك)", "Cielo nocturno (animado)", "夜空 (アニメ)", "夜空 (动画)"),
    "Rainy window (animated)": ("نافذة ممطرة (متحرك)", "Ventana con lluvia (animado)", "雨の窓 (アニメ)", "雨天窗户 (动画)"),
    "Synthwave (animated)": ("سينث ويف (متحرك)", "Synthwave (animado)", "シンセウェーブ (アニメ)", "合成波 (动画)"),
    "Arcade (animated)": ("أركيد (متحرك)", "Arcade (animado)", "アーケード (アニメ)", "街机 (动画)"),
    "Weather (live, animated)": ("الطقس (مباشر، متحرك)", "Tiempo (en vivo, animado)", "天気 (ライブ・アニメ)",
                                 "天气 (实时, 动画)"),
    # ---- weather
    "Clear": ("صافٍ", "Despejado", "晴れ", "晴"),
    "Partly cloudy": ("غائم جزئياً", "Parcialmente nublado", "晴れ時々くもり", "多云"),
    "Cloudy": ("غائم", "Nublado", "くもり", "阴"),
    "Fog": ("ضباب", "Niebla", "霧", "雾"),
    "Rain": ("مطر", "Lluvia", "雨", "雨"),
    "Snow": ("ثلج", "Nieve", "雪", "雪"),
    "Thunderstorm": ("عاصفة رعدية", "Tormenta", "雷雨", "雷雨"),
    "Live": ("مباشر", "En vivo", "ライブ", "实时"),
    "Sun": ("شمس", "Sol", "晴れ", "晴天"),
    "Some clouds": ("بعض الغيوم", "Algunas nubes", "少し雲", "少云"),
    "Clouds": ("غيوم", "Nubes", "くもり", "云"),
    "Storm": ("عاصفة", "Tormenta", "嵐", "暴风雨"),
    "Night": ("ليل", "Noche", "夜", "夜晚"),
    # ---- skins you upload
    "That file isn't a picture Peelpad can read. Use a PNG.": (
        "هذا الملف ليس صورة يستطيع Peelpad قراءتها. استخدم PNG.", "Ese archivo no es una imagen que Peelpad pueda leer. Usa un PNG.",
        "Peelpad が読める画像ではありません。PNG を使ってください。", "这个文件不是 Peelpad 能读取的图片。请使用 PNG。"),
    "It has no transparent parts, so the note will be its whole rectangle.": (
        "ليس فيها أجزاء شفافة، فستكون الملاحظة مستطيلها كاملاً.", "No tiene partes transparentes, así que la nota será todo el rectángulo.",
        "透明な部分がないので、メモは四角形全体になります。", "它没有透明部分, 所以便签会是整个矩形。"),
    "It's only {w} x {h} px, so it may look soft. {best} x {best} px is best.": (
        "حجمها {w} × {h} بكسل فقط، فقد تبدو ضبابية. الأفضل {best} × {best} بكسل.",
        "Solo mide {w} x {h} px, así que puede verse borrosa. Lo mejor es {best} x {best} px.",
        "{w} x {h} px しかないので、ぼやけるかもしれません。{best} x {best} px が最適です。",
        "它只有 {w} x {h} 像素, 可能会模糊。最好是 {best} x {best} 像素。"),
    "It's very long or very tall; new notes will take that shape.": (
        "إنها طويلة جداً أو عريضة جداً؛ ستأخذ الملاحظات الجديدة هذا الشكل.", "Es muy larga o muy alta; las notas nuevas tomarán esa forma.",
        "とても横長か縦長です。新しいメモはその形になります。", "它非常长或非常高; 新便签会是这个形状。"),
    "Couldn't save the skin.": ("تعذّر حفظ الشكل.", "No se pudo guardar el aspecto.", "スキンを保存できませんでした。", "无法保存皮肤。"),
    "Its checkerboard background was painted in, not transparent; Peelpad removed it.": (
        "خلفية المربعات كانت مرسومة وليست شفافة؛ أزالها Peelpad.", "Su fondo de cuadros estaba pintado, no era transparente; Peelpad lo quitó.",
        "市松模様の背景は透明ではなく描かれていたので、Peelpad が取り除きました。", "它的棋盘格背景是画上去的, 不是透明的; Peelpad 已把它去掉。"),
    "It has a lot of frames; Peelpad plays the first 150.": (
        "فيها إطارات كثيرة؛ يعرض Peelpad أول 150.", "Tiene muchos fotogramas; Peelpad reproduce los primeros 150.",
        "フレームが多いので、Peelpad は最初の150枚を再生します。", "它的帧很多; Peelpad 播放前150帧。"),
}


def system_language() -> str:
    """The language Windows uses, if Peelpad speaks it (else English)."""
    from PySide6.QtCore import QLocale

    code = QLocale.system().name()[:2]
    return code if code in ORDER else "en"


def set_language(choice: str) -> str:
    """'auto' or a language code. Returns the language now in use."""
    global LANG
    LANG = system_language() if choice == "auto" else (choice if choice in ORDER else "en")
    return LANG


def right_to_left() -> bool:
    return LANG == "ar"


def tr(text: str) -> str:
    if LANG == "en":
        return text
    row = T.get(text)
    return row[ORDER.index(LANG)] if row else text


def _locale():
    from PySide6.QtCore import QLocale

    return QLocale(LOCALES.get(LANG, "en_GB"))


def weekday_names() -> list[str]:
    """Monday to Sunday, short, in the language in use."""
    from PySide6.QtCore import QLocale

    loc = _locale()
    return [loc.dayName(i, QLocale.FormatType.ShortFormat) for i in range(1, 8)]


def month_title(day: date) -> str:
    from PySide6.QtCore import QDate

    return _locale().toString(QDate(day.year, day.month, 1), "MMMM yyyy")


def date_text(day: date) -> str:
    from PySide6.QtCore import QDate, QLocale

    return _locale().toString(QDate(day.year, day.month, day.day), QLocale.FormatType.LongFormat)
