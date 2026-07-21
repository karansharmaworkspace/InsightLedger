"""Multi-language support for DOCOKF dashboard and detection output.

Uses dynamic Google Translate via deep-translator for unlimited languages,
with manual dictionary fallback for P&ID class name accuracy.
"""

import functools

from utils.translator import get_translator

# 32-class P&ID symbol translations
CLASS_NAMES = {
    "en": {
        "Gate_Valve_Vertical": "Gate Valve (Vertical)",
        "Globe_Valve": "Globe Valve",
        "Ball_Valve": "Ball Valve",
        "Gate_Valve_Horizontal": "Gate Valve (Horizontal)",
        "Butterfly_Valve": "Butterfly Valve",
        "Plug_Valve": "Plug Valve",
        "Check_Valve": "Check Valve",
        "Control_Valve_Diaphragm": "Control Valve (Diaphragm)",
        "Pressure_Relief_Valve": "Pressure Relief Valve",
        "Angle_Valve": "Angle Valve",
        "Needle_Valve": "Needle Valve",
        "Pinch_Valve": "Pinch Valve",
        "Diaphragm_Valve": "Diaphragm Valve",
        "Control_Valve_Alternate": "Control Valve (Alternate)",
        "Centrifugal_Pump": "Centrifugal Pump",
        "Rotary_Pump": "Rotary Pump",
        "Piston_Cylinder_Actuator": "Piston / Cylinder Actuator",
        "Vertical_Vessel": "Vertical Vessel",
        "Centrifugal_Fan": "Centrifugal Fan",
        "Drain_Funnel": "Drain / Funnel",
        "Orifice_Plate": "Orifice Plate",
        "Heat_Exchanger": "Heat Exchanger",
        "Air_Cooler": "Air Cooler",
        "Y-Strainer": "Y-Strainer",
        "Motorized_Actuator": "Motorized Actuator",
        "Glass_Lined_Reactor": "Glass-Lined Reactor",
        "Restriction_Orifice": "Restriction Orifice",
        "Safety_Discrete_Logic": "Safety (Discrete Logic)",
        "Digital_Data_Link": "Digital Data Link",
        "Status_Indicator": "Status Indicator",
        "Position_Switch_Closed": "Position Switch (Closed)",
        "Level_Gauge": "Level Gauge",
    },
    "ja": {
        "Gate_Valve_Vertical": "ゲートバルブ（垂直）",
        "Globe_Valve": "グローブバルブ",
        "Ball_Valve": "ボールバルブ",
        "Gate_Valve_Horizontal": "ゲートバルブ（水平）",
        "Butterfly_Valve": "バタフライバルブ",
        "Plug_Valve": "プラグバルブ",
        "Check_Valve": "逆止め弁",
        "Control_Valve_Diaphragm": "調節弁（ダイヤフラム）",
        "Pressure_Relief_Valve": "安全弁",
        "Angle_Valve": "アングルバルブ",
        "Needle_Valve": "ニードルバルブ",
        "Pinch_Valve": "ピンチバルブ",
        "Diaphragm_Valve": "ダイヤフラムバルブ",
        "Control_Valve_Alternate": "調節弁（別形式）",
        "Centrifugal_Pump": "遠心ポンプ",
        "Rotary_Pump": "回転ポンプ",
        "Piston_Cylinder_Actuator": "ピストン/シリンダーアクチュエータ",
        "Vertical_Vessel": "立型容器",
        "Centrifugal_Fan": "遠心ファン",
        "Drain_Funnel": "ドレン/漏斗",
        "Orifice_Plate": "オリフィス板",
        "Heat_Exchanger": "熱交換器",
        "Air_Cooler": "空気冷却器",
        "Y-Strainer": "Y型ストレーナ",
        "Motorized_Actuator": "電動アクチュエータ",
        "Glass_Lined_Reactor": "ガラスライニング反応器",
        "Restriction_Orifice": "制限オリフィス",
        "Safety_Discrete_Logic": "安全（ディスクリートロジック）",
        "Digital_Data_Link": "デジタルデータリンク",
        "Status_Indicator": "状態表示器",
        "Position_Switch_Closed": "位置スイッチ（閉）",
        "Level_Gauge": "レベル計",
    },
    "zh": {
        "Gate_Valve_Vertical": "闸阀（垂直）",
        "Globe_Valve": "截止阀",
        "Ball_Valve": "球阀",
        "Gate_Valve_Horizontal": "闸阀（水平）",
        "Butterfly_Valve": "蝶阀",
        "Plug_Valve": "旋塞阀",
        "Check_Valve": "止回阀",
        "Control_Valve_Diaphragm": "调节阀（隔膜式）",
        "Pressure_Relief_Valve": "安全阀",
        "Angle_Valve": "角式截止阀",
        "Needle_Valve": "针形阀",
        "Pinch_Valve": "夹管阀",
        "Diaphragm_Valve": "隔膜阀",
        "Control_Valve_Alternate": "调节阀（其他）",
        "Centrifugal_Pump": "离心泵",
        "Rotary_Pump": "旋转泵",
        "Piston_Cylinder_Actuator": "活塞/气缸执行机构",
        "Vertical_Vessel": "立式容器",
        "Centrifugal_Fan": "离心风机",
        "Drain_Funnel": "排水/漏斗",
        "Orifice_Plate": "孔板",
        "Heat_Exchanger": "换热器",
        "Air_Cooler": "空冷器",
        "Y-Strainer": "Y型过滤器",
        "Motorized_Actuator": "电动执行机构",
        "Glass_Lined_Reactor": "搪玻璃反应釜",
        "Restriction_Orifice": "限流孔板",
        "Safety_Discrete_Logic": "安全（离散逻辑）",
        "Digital_Data_Link": "数字数据链路",
        "Status_Indicator": "状态指示器",
        "Position_Switch_Closed": "位置开关（闭合）",
        "Level_Gauge": "液位计",
    },
    "ko": {
        "Gate_Valve_Vertical": "게이트 밸브 (수직)",
        "Globe_Valve": "글로브 밸브",
        "Ball_Valve": "볼 밸브",
        "Gate_Valve_Horizontal": "게이트 밸브 (수평)",
        "Butterfly_Valve": "버터플라이 밸브",
        "Plug_Valve": "플러그 밸브",
        "Check_Valve": "체크 밸브",
        "Control_Valve_Diaphragm": "제어 밸브 (격막식)",
        "Pressure_Relief_Valve": "안전 밸브",
        "Angle_Valve": "앵글 밸브",
        "Needle_Valve": "니들 밸브",
        "Pinch_Valve": "핀치 밸브",
        "Diaphragm_Valve": "격막 밸브",
        "Control_Valve_Alternate": "제어 밸브 (대체식)",
        "Centrifugal_Pump": "원심 펌프",
        "Rotary_Pump": "회전 펌프",
        "Piston_Cylinder_Actuator": "피스톤/실린더 액추에이터",
        "Vertical_Vessel": "수직 용기",
        "Centrifugal_Fan": "원심 팬",
        "Drain_Funnel": "드레인/깔때기",
        "Orifice_Plate": "오리피스 플레이트",
        "Heat_Exchanger": "열교환기",
        "Air_Cooler": "공기 냉각기",
        "Y-Strainer": "Y형 스트레이너",
        "Motorized_Actuator": "전동 액추에이터",
        "Glass_Lined_Reactor": "유리 라이닝 반응기",
        "Restriction_Orifice": "제한 오리피스",
        "Safety_Discrete_Logic": "안전 (이산 논리)",
        "Digital_Data_Link": "디지털 데이터 링크",
        "Status_Indicator": "상태 표시기",
        "Position_Switch_Closed": "위치 스위치 (폐쇄)",
        "Level_Gauge": "레벨 게이지",
    },
    "de": {
        "Gate_Valve_Vertical": "Schieber (senkrecht)",
        "Globe_Valve": "Ventil",
        "Ball_Valve": "Kugelhahn",
        "Gate_Valve_Horizontal": "Schieber (waagerecht)",
        "Butterfly_Valve": "Absperrklappe",
        "Plug_Valve": "Kükenhahn",
        "Check_Valve": "Rückschlagventil",
        "Control_Valve_Diaphragm": "Regelventil (Membran)",
        "Pressure_Relief_Valve": "Sicherheitsventil",
        "Angle_Valve": "Eckventil",
        "Needle_Valve": "Nadelventil",
        "Pinch_Valve": "Quetschventil",
        "Diaphragm_Valve": "Membranventil",
        "Control_Valve_Alternate": "Regelventil (alternativ)",
        "Centrifugal_Pump": "Kreiselpumpe",
        "Rotary_Pump": "Rotationspumpe",
        "Piston_Cylinder_Actuator": "Kolben-/Zylinderantrieb",
        "Vertical_Vessel": "stehender Behälter",
        "Centrifugal_Fan": "Zentrifugalgebläse",
        "Drain_Funnel": "Ablauf/Trichter",
        "Orifice_Plate": "Blende",
        "Heat_Exchanger": "Wärmetauscher",
        "Air_Cooler": "Luftkühler",
        "Y-Strainer": "Y-Sieb",
        "Motorized_Actuator": "motorischer Antrieb",
        "Glass_Lined_Reactor": "glasemaillierter Reaktor",
        "Restriction_Orifice": "Drosselblende",
        "Safety_Discrete_Logic": "Sicherheit (Diskretlogik)",
        "Digital_Data_Link": "digitale Datenverbindung",
        "Status_Indicator": "Statusanzeige",
        "Position_Switch_Closed": "Endlagenschalter (geschlossen)",
        "Level_Gauge": "Füllstandsanzeige",
    },
    "es": {
        "Gate_Valve_Vertical": "Válvula de Compuerta (Vertical)",
        "Globe_Valve": "Válvula de Globo",
        "Ball_Valve": "Válvula de Bola",
        "Gate_Valve_Horizontal": "Válvula de Compuerta (Horizontal)",
        "Butterfly_Valve": "Válvula de Mariposa",
        "Plug_Valve": "Válvula de Tapón",
        "Check_Valve": "Válvula de Retención",
        "Control_Valve_Diaphragm": "Válvula de Control (Diafragma)",
        "Pressure_Relief_Valve": "Válvula de Seguridad",
        "Angle_Valve": "Válvula en Ángulo",
        "Needle_Valve": "Válvula de Aguja",
        "Pinch_Valve": "Válvula de Pinzamiento",
        "Diaphragm_Valve": "Válvula de Diafragma",
        "Control_Valve_Alternate": "Válvula de Control (Alternativa)",
        "Centrifugal_Pump": "Bomba Centrífuga",
        "Rotary_Pump": "Bomba Rotativa",
        "Piston_Cylinder_Actuator": "Actuador de Pistón/Cilindro",
        "Vertical_Vessel": "Recipiente Vertical",
        "Centrifugal_Fan": "Ventilador Centrífugo",
        "Drain_Funnel": "Drenaje/Embudo",
        "Orifice_Plate": "Placa de Orificio",
        "Heat_Exchanger": "Intercambiador de Calor",
        "Air_Cooler": "Enfriador de Aire",
        "Y-Strainer": "Filtro en Y",
        "Motorized_Actuator": "Actuador Motorizado",
        "Glass_Lined_Reactor": "Reactor de Vidrio Esmaltado",
        "Restriction_Orifice": "Orificio de Restricción",
        "Safety_Discrete_Logic": "Seguridad (Lógica Discreta)",
        "Digital_Data_Link": "Enlace de Datos Digital",
        "Status_Indicator": "Indicador de Estado",
        "Position_Switch_Closed": "Interruptor de Posición (Cerrado)",
        "Level_Gauge": "Indicador de Nivel",
    },
    "fr": {
        "Gate_Valve_Vertical": "Robinet-vanne (Vertical)",
        "Globe_Valve": "Robinet à soupape",
        "Ball_Valve": "Robinet à bille",
        "Gate_Valve_Horizontal": "Robinet-vanne (Horizontal)",
        "Butterfly_Valve": "Papillon",
        "Plug_Valve": "Robinet à tournant",
        "Check_Valve": "Clapet anti-retour",
        "Control_Valve_Diaphragm": "Vanne de régulation (Membrane)",
        "Pressure_Relief_Valve": "Soupape de sûreté",
        "Angle_Valve": "Robinet d'équerre",
        "Needle_Valve": "Vanne à pointeau",
        "Pinch_Valve": "Vanne à pincement",
        "Diaphragm_Valve": "Vanne à membrane",
        "Control_Valve_Alternate": "Vanne de régulation (Alternative)",
        "Centrifugal_Pump": "Pompe centrifuge",
        "Rotary_Pump": "Pompe rotative",
        "Piston_Cylinder_Actuator": "Actionneur piston/vérin",
        "Vertical_Vessel": "Récipient vertical",
        "Centrifugal_Fan": "Ventilateur centrifuge",
        "Drain_Funnel": "Vidange/Entonnoir",
        "Orifice_Plate": "Plaque à orifice",
        "Heat_Exchanger": "Échangeur de chaleur",
        "Air_Cooler": "Aéroréfrigérant",
        "Y-Strainer": "Filtre en Y",
        "Motorized_Actuator": "Actionneur motorisé",
        "Glass_Lined_Reactor": "Réacteur émaillé",
        "Restriction_Orifice": "Orifice de restriction",
        "Safety_Discrete_Logic": "Sécurité (Logique discrète)",
        "Digital_Data_Link": "Liaison de données numérique",
        "Status_Indicator": "Indicateur d'état",
        "Position_Switch_Closed": "Contact de position (Fermé)",
        "Level_Gauge": "Indicateur de niveau",
    },
    "it": {
        "Gate_Valve_Vertical": "Valvola a saracinesca (Verticale)",
        "Globe_Valve": "Valvola a globo",
        "Ball_Valve": "Valvola a sfera",
        "Gate_Valve_Horizontal": "Valvola a saracinesca (Orizzontale)",
        "Butterfly_Valve": "Valvola a farfalla",
        "Plug_Valve": "Valvola a maschio",
        "Check_Valve": "Valvola di ritegno",
        "Control_Valve_Diaphragm": "Valvola di regolazione (A membrana)",
        "Pressure_Relief_Valve": "Valvola di sicurezza",
        "Angle_Valve": "Valvola ad angolo",
        "Needle_Valve": "Valvola a spillo",
        "Pinch_Valve": "Valvola a pizzicamento",
        "Diaphragm_Valve": "Valvola a membrana",
        "Control_Valve_Alternate": "Valvola di regolazione (Alternativa)",
        "Centrifugal_Pump": "Pompa centrifuga",
        "Rotary_Pump": "Pompa rotativa",
        "Piston_Cylinder_Actuator": "Attuatore pistone/cilindro",
        "Vertical_Vessel": "Recipiente verticale",
        "Centrifugal_Fan": "Ventilatore centrifugo",
        "Drain_Funnel": "Scarico/Imbuto",
        "Orifice_Plate": "Piastra a foro",
        "Heat_Exchanger": "Scambiatore di calore",
        "Air_Cooler": "Raffreddatore d'aria",
        "Y-Strainer": "Filtro a Y",
        "Motorized_Actuator": "Attuatore motorizzato",
        "Glass_Lined_Reactor": "Reattore vetrificato",
        "Restriction_Orifice": "Orifizio di restrizione",
        "Safety_Discrete_Logic": "Sicurezza (Logica discreta)",
        "Digital_Data_Link": "Collegamento dati digitale",
        "Status_Indicator": "Indicatore di stato",
        "Position_Switch_Closed": "Finecorsa (Chiuso)",
        "Level_Gauge": "Indicatore di livello",
    },
    "pt": {
        "Gate_Valve_Vertical": "Válvula Gaveta (Vertical)",
        "Globe_Valve": "Válvula Globo",
        "Ball_Valve": "Válvula Esfera",
        "Gate_Valve_Horizontal": "Válvula Gaveta (Horizontal)",
        "Butterfly_Valve": "Válvula Borboleta",
        "Plug_Valve": "Válvula Macho",
        "Check_Valve": "Válvula de Retenção",
        "Control_Valve_Diaphragm": "Válvula de Controle (Diafragma)",
        "Pressure_Relief_Valve": "Válvula de Segurança",
        "Angle_Valve": "Válvula Angular",
        "Needle_Valve": "Válvula Agulha",
        "Pinch_Valve": "Válvula de Pinçamento",
        "Diaphragm_Valve": "Válvula de Diafragma",
        "Control_Valve_Alternate": "Válvula de Controle (Alternativa)",
        "Centrifugal_Pump": "Bomba Centrífuga",
        "Rotary_Pump": "Bomba Rotativa",
        "Piston_Cylinder_Actuator": "Atuador Pistão/Cilindro",
        "Vertical_Vessel": "Vaso Vertical",
        "Centrifugal_Fan": "Ventilador Centrífugo",
        "Drain_Funnel": "Dreno/Funil",
        "Orifice_Plate": "Placa de Orifício",
        "Heat_Exchanger": "Trocador de Calor",
        "Air_Cooler": "Resfriador de Ar",
        "Y-Strainer": "Filtro Y",
        "Motorized_Actuator": "Atuador Motorizado",
        "Glass_Lined_Reactor": "Reator Vitrificado",
        "Restriction_Orifice": "Orifício de Restrição",
        "Safety_Discrete_Logic": "Segurança (Lógica Discreta)",
        "Digital_Data_Link": "Link de Dados Digital",
        "Status_Indicator": "Indicador de Status",
        "Position_Switch_Closed": "Chave de Posição (Fechada)",
        "Level_Gauge": "Indicador de Nível",
    },
    "ru": {
        "Gate_Valve_Vertical": "Задвижка (Вертикальная)",
        "Globe_Valve": "Клапан запорный",
        "Ball_Valve": "Шаровой кран",
        "Gate_Valve_Horizontal": "Задвижка (Горизонтальная)",
        "Butterfly_Valve": "Дисковый затвор",
        "Plug_Valve": "Кран пробковый",
        "Check_Valve": "Обратный клапан",
        "Control_Valve_Diaphragm": "Регулирующий клапан (Мембранный)",
        "Pressure_Relief_Valve": "Предохранительный клапан",
        "Angle_Valve": "Угловой клапан",
        "Needle_Valve": "Игольчатый клапан",
        "Pinch_Valve": "Шланговый клапан",
        "Diaphragm_Valve": "Мембранный клапан",
        "Control_Valve_Alternate": "Регулирующий клапан (Альтернативный)",
        "Centrifugal_Pump": "Центробежный насос",
        "Rotary_Pump": "Роторный насос",
        "Piston_Cylinder_Actuator": "Поршневой/цилиндровый привод",
        "Vertical_Vessel": "Вертикальный сосуд",
        "Centrifugal_Fan": "Центробежный вентилятор",
        "Drain_Funnel": "Дренаж/Воронка",
        "Orifice_Plate": "Диафрагма",
        "Heat_Exchanger": "Теплообменник",
        "Air_Cooler": "Воздухоохладитель",
        "Y-Strainer": "Фильтр Y-образный",
        "Motorized_Actuator": "Электропривод",
        "Glass_Lined_Reactor": "Реактор со стеклянным покрытием",
        "Restriction_Orifice": "Шайба дроссельная",
        "Safety_Discrete_Logic": "Безопасность (Дискретная логика)",
        "Digital_Data_Link": "Цифровая линия связи",
        "Status_Indicator": "Индикатор состояния",
        "Position_Switch_Closed": "Концевой выключатель (Закрыт)",
        "Level_Gauge": "Уровнемер",
    },
    "ar": {
        "Gate_Valve_Vertical": "صمام بوابة (رأسي)",
        "Globe_Valve": "صمام كروي",
        "Ball_Valve": "صمام كروي",
        "Gate_Valve_Horizontal": "صمام بوابة (أفقي)",
        "Butterfly_Valve": "صمام فراشة",
        "Plug_Valve": "صمام سدادة",
        "Check_Valve": "صمام عدم رجوع",
        "Control_Valve_Diaphragm": "صمام تحكم (غشائي)",
        "Pressure_Relief_Valve": "صمام أمان",
        "Angle_Valve": "صمام زاوي",
        "Needle_Valve": "صمام إبري",
        "Pinch_Valve": "صمام قرصي",
        "Diaphragm_Valve": "صمام غشائي",
        "Control_Valve_Alternate": "صمام تحكم (بديل)",
        "Centrifugal_Pump": "مضخة طرد مركزي",
        "Rotary_Pump": "مضخة دوارة",
        "Piston_Cylinder_Actuator": "مشغل مكبس/أسطوانة",
        "Vertical_Vessel": "وعاء عمودي",
        "Centrifugal_Fan": "مروحة طرد مركزي",
        "Drain_Funnel": "تصريف/قمع",
        "Orifice_Plate": "لوحة فتحة",
        "Heat_Exchanger": "مبادل حراري",
        "Air_Cooler": "مبرد هواء",
        "Y-Strainer": "مصفاة Y",
        "Motorized_Actuator": "مشغل آلي",
        "Glass_Lined_Reactor": "مفاعل مطلي بالزجاج",
        "Restriction_Orifice": "فتحة تخفيض",
        "Safety_Discrete_Logic": "سلامة (منطق متقطع)",
        "Digital_Data_Link": "رابط بيانات رقمي",
        "Status_Indicator": "مؤشر الحالة",
        "Position_Switch_Closed": "مفتاح وضع (مغلق)",
        "Level_Gauge": "مقياس مستوى",
    },
}

# ---------------------------------------------------------------------------
# language code mapping: internal → Google Translate
# ---------------------------------------------------------------------------
GOOGLE_LANG_MAP = {
    "en": "en",
    "ja": "ja",
    "zh": "zh-CN",
    "ko": "ko",
    "de": "de",
    "es": "es",
    "fr": "fr",
    "it": "it",
    "pt": "pt",
    "ru": "ru",
    "ar": "ar",
    "hi": "hi",
    "nl": "nl",
    "pl": "pl",
    "tr": "tr",
    "vi": "vi",
    "th": "th",
    "sv": "sv",
    "da": "da",
    "fi": "fi",
    "cs": "cs",
    "ro": "ro",
    "hu": "hu",
    "el": "el",
    "uk": "uk",
    "he": "he",
    "id": "id",
    "ms": "ms",
}

# ---------------------------------------------------------------------------
# UI dropdown: (internal_code, display_name)
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES = [
    ("en", "English"),
    ("ja", "Japanese"),
    ("zh", "Chinese (Simplified)"),
    ("ko", "Korean"),
    ("de", "German"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("ru", "Russian"),
    ("nl", "Dutch"),
    ("pl", "Polish"),
    ("tr", "Turkish"),
    ("vi", "Vietnamese"),
    ("th", "Thai"),
    ("ar", "Arabic"),
    ("hi", "Hindi"),
    ("sv", "Swedish"),
    ("da", "Danish"),
    ("fi", "Finnish"),
    ("cs", "Czech"),
    ("ro", "Romanian"),
    ("hu", "Hungarian"),
    ("el", "Greek"),
    ("uk", "Ukrainian"),
    ("he", "Hebrew"),
    ("id", "Indonesian"),
    ("ms", "Malay"),
]

# OCR language codes for easyocr
OCR_LANG = {
    "en": ["en"],
    "ja": ["ja", "en"],
    "zh": ["ch_sim", "en"],
    "ko": ["ko", "en"],
    "de": ["de", "en"],
    "es": ["es", "en"],
    "fr": ["fr", "en"],
    "it": ["it", "en"],
    "pt": ["pt", "en"],
    "ru": ["ru", "en"],
    "nl": ["nl", "en"],
    "pl": ["pl", "en"],
    "tr": ["tr", "en"],
    "vi": ["vi", "en"],
    "th": ["th", "en"],
    "ar": ["ar", "en"],
    "hi": ["hi", "en"],
    "sv": ["sv", "en"],
    "da": ["da", "en"],
    "fi": ["fi", "en"],
    "cs": ["cs", "en"],
    "ro": ["ro", "en"],
    "hu": ["hu", "en"],
    "el": ["el", "en"],
    "uk": ["uk", "en"],
    "he": ["he", "en"],
    "id": ["id", "en"],
    "ms": ["ms", "en"],
}

# GUI static text translations
GUI_TEXT = {
    "en": {
        "window_title": "DOCOKF - Universal Intelligence Engine",
        "topology_explorer": "Topology Explorer",
        "ai_assistant": "AI Assistant",
        "detection_metadata": "Detection Metadata",
        "neural_console": "Neural Console",
        "open_diagram": "Open Diagram",
        "crop_pid": "Crop P&ID",
        "confirm_crop": "✓ Confirm Crop",
        "cancel_crop": "✕ Cancel Crop",
        "zoom_in": "Zoom +",
        "zoom_out": "Zoom -",
        "run_digitization": "Run Digitization",
        "export_dexpi": "Export DEXPI",
        "language": "Language",
        "ready": "Ready",
        "no_symbol": "No symbol",
        "search_classes": "Search classes...",
        "no_class": "No class selected",
        "confirm": "Confirm",
        "new_class": "New Class",
        "class_name_placeholder": "Class name...",
        "create_select": "Create & Select",
        "ask_placeholder": "Ask InsightLedger AI Assistant...",
        "load_pid": "Load a P&ID diagram to begin...",
        "hierarchy": "Hierarchy",
        "reclassify": "Reclassify Symbol",
    },
    "ja": {
        "window_title": "DOCOKF - 汎用インテリジェンスエンジン",
        "topology_explorer": "トポロジエクスプローラ",
        "ai_assistant": "AIアシスタント",
        "detection_metadata": "検出メタデータ",
        "neural_console": "ニューラルコンソール",
        "open_diagram": "図面を開く",
        "crop_pid": "P&IDを切り抜き",
        "confirm_crop": "✓ 切り抜き確定",
        "cancel_crop": "✕ キャンセル",
        "zoom_in": "拡大 +",
        "zoom_out": "縮小 -",
        "run_digitization": "デジタル化実行",
        "export_dexpi": "DEXPIエクスポート",
        "language": "言語",
        "ready": "準備完了",
        "no_symbol": "シンボルなし",
        "search_classes": "クラスを検索...",
        "no_class": "クラス未選択",
        "confirm": "確定",
        "new_class": "新規クラス",
        "class_name_placeholder": "クラス名...",
        "create_select": "作成して選択",
        "ask_placeholder": "InsightLedger AIアシスタントに質問...",
        "load_pid": "P&ID図面を読み込んでください...",
        "hierarchy": "階層",
        "reclassify": "シンボル再分類",
    },
    "zh": {
        "window_title": "DOCOKF - 通用智能引擎",
        "topology_explorer": "拓扑浏览器",
        "ai_assistant": "AI助手",
        "detection_metadata": "检测元数据",
        "neural_console": "神经控制台",
        "open_diagram": "打开图纸",
        "crop_pid": "裁剪P&ID",
        "confirm_crop": "✓ 确认裁剪",
        "cancel_crop": "✕ 取消",
        "zoom_in": "放大 +",
        "zoom_out": "缩小 -",
        "run_digitization": "运行数字化",
        "export_dexpi": "导出DEXPI",
        "language": "语言",
        "ready": "就绪",
        "no_symbol": "无符号",
        "search_classes": "搜索类别...",
        "no_class": "未选择类别",
        "confirm": "确认",
        "new_class": "新类别",
        "class_name_placeholder": "类别名称...",
        "create_select": "创建并选择",
        "ask_placeholder": "询问InsightLedger AI助手...",
        "load_pid": "请加载P&ID图纸...",
        "hierarchy": "层级",
        "reclassify": "重新分类符号",
    },
}

# Legend parent categories
PARENT_CLASSES = {
    "en": {
        "Valves": "Valves",
        "Pumps": "Pumps",
        "Compressors": "Compressors",
        "Centrifuges": "Centrifuges",
        "Crushers": "Crushers",
        "Dryers": "Dryers",
        "Filters": "Filters",
        "Heat_Exchangers": "Heat Exchangers",
        "Instruments": "Instruments",
        "Mixers": "Mixers",
        "Motors": "Motors",
        "Vessels": "Vessels",
        "Piping_and_Connecting_Shapes": "Piping & Connecting",
        "Peripheral": "Peripheral",
        "General": "General",
    },
    "ja": {
        "Valves": "バルブ",
        "Pumps": "ポンプ",
        "Compressors": "圧縮機",
        "Centrifuges": "遠心分離機",
        "Crushers": "破砕機",
        "Dryers": "乾燥機",
        "Filters": "フィルター",
        "Heat_Exchangers": "熱交換器",
        "Instruments": "計器",
        "Mixers": "混合機",
        "Motors": "モーター",
        "Vessels": "容器",
        "Piping_and_Connecting_Shapes": "配管・接続形状",
        "Peripheral": "周辺機器",
        "General": "一般",
    },
    "zh": {
        "Valves": "阀门",
        "Pumps": "泵",
        "Compressors": "压缩机",
        "Centrifuges": "离心机",
        "Crushers": "破碎机",
        "Dryers": "干燥器",
        "Filters": "过滤器",
        "Heat_Exchangers": "换热器",
        "Instruments": "仪表",
        "Mixers": "搅拌器",
        "Motors": "电机",
        "Vessels": "容器",
        "Piping_and_Connecting_Shapes": "管道及连接件",
        "Peripheral": "外围设备",
        "General": "通用",
    },
    "fr": {
        "Valves": "Vannes",
        "Pumps": "Pompes",
        "Compressors": "Compresseurs",
        "Centrifuges": "Centrifugeuses",
        "Crushers": "Concasseurs",
        "Dryers": "Sécheurs",
        "Filters": "Filtres",
        "Heat_Exchangers": "Échangeurs de chaleur",
        "Instruments": "Instruments",
        "Mixers": "Mélangeurs",
        "Motors": "Moteurs",
        "Vessels": "Récipients",
        "Piping_and_Connecting_Shapes": "Tuyauterie & Raccordement",
        "Peripheral": "Périphérique",
        "General": "Général",
    },
    "it": {
        "Valves": "Valvole",
        "Pumps": "Pompe",
        "Compressors": "Compressori",
        "Centrifuges": "Centrifughe",
        "Crushers": "Frantumatori",
        "Dryers": "Essiccatori",
        "Filters": "Filtri",
        "Heat_Exchangers": "Scambiatori di calore",
        "Instruments": "Strumenti",
        "Mixers": "Miscelatori",
        "Motors": "Motori",
        "Vessels": "Recipienti",
        "Piping_and_Connecting_Shapes": "Tubazioni & Collegamenti",
        "Peripheral": "Periferiche",
        "General": "Generale",
    },
    "pt": {
        "Valves": "Válvulas",
        "Pumps": "Bombas",
        "Compressors": "Compressores",
        "Centrifuges": "Centrífugas",
        "Crushers": "Britadores",
        "Dryers": "Secadores",
        "Filters": "Filtros",
        "Heat_Exchangers": "Trocadores de calor",
        "Instruments": "Instrumentos",
        "Mixers": "Misturadores",
        "Motors": "Motores",
        "Vessels": "Vasos",
        "Piping_and_Connecting_Shapes": "Tubulação & Conexão",
        "Peripheral": "Periférico",
        "General": "Geral",
    },
    "ru": {
        "Valves": "Арматура",
        "Pumps": "Насосы",
        "Compressors": "Компрессоры",
        "Centrifuges": "Центрифуги",
        "Crushers": "Дробилки",
        "Dryers": "Сушилки",
        "Filters": "Фильтры",
        "Heat_Exchangers": "Теплообменники",
        "Instruments": "Приборы",
        "Mixers": "Смесители",
        "Motors": "Двигатели",
        "Vessels": "Сосуды",
        "Piping_and_Connecting_Shapes": "Трубопроводы и соединения",
        "Peripheral": "Периферийное",
        "General": "Общее",
    },
    "ar": {
        "Valves": "الصمامات",
        "Pumps": "المضخات",
        "Compressors": "الضواغط",
        "Centrifuges": "أجهزة الطرد المركزي",
        "Crushers": "الكسارات",
        "Dryers": "المجففات",
        "Filters": "المرشحات",
        "Heat_Exchangers": "المبادلات الحرارية",
        "Instruments": "الأجهزة",
        "Mixers": "الخلاطات",
        "Motors": "المحركات",
        "Vessels": "الأوعية",
        "Piping_and_Connecting_Shapes": "الأنابيب والتوصيلات",
        "Peripheral": "ملحقات",
        "General": "عام",
    },
}

# Table column headers
TABLE_HEADERS = {
    "en": ["ID", "Class", "Fine Class", "Labels", "Coordinates"],
    "ja": ["ID", "クラス", "詳細クラス", "ラベル", "座標"],
    "zh": ["ID", "类别", "细分类别", "标签", "坐标"],
    "fr": ["ID", "Classe", "Sous-classe", "Étiquettes", "Coordonnées"],
    "it": ["ID", "Classe", "Sottoclasse", "Etichette", "Coordinate"],
    "pt": ["ID", "Classe", "Subclasse", "Rótulos", "Coordenadas"],
    "ru": ["ID", "Класс", "Подкласс", "Метки", "Координаты"],
    "ar": ["المعرف", "الفئة", "الفئة الفرعية", "التسميات", "الإحداثيات"],
}


# module-level translator singleton (lazy init)
_translator = None


def _get_trans():
    global _translator
    if _translator is None:
        _translator = get_translator()
    return _translator


def tr_class(class_key, lang="en"):
    """Translate a P&ID class key to the target language.

    Tries the manual dictionary first (accurate for domain terms), then
    falls back to dynamic Google Translate for any language.
    """
    if lang == "en":
        return CLASS_NAMES["en"].get(class_key, class_key)
    # fast path: dict exists
    lang_map = CLASS_NAMES.get(lang)
    if lang_map and class_key in lang_map:
        return lang_map[class_key]
    # fallback: translate English display name
    en_text = CLASS_NAMES["en"].get(class_key, class_key)
    gt_lang = GOOGLE_LANG_MAP.get(lang, lang)
    try:
        return _get_trans().translate(en_text, gt_lang)
    except Exception:
        return en_text


@functools.lru_cache(maxsize=512)
def _cached_translate(text: str, target: str) -> str:
    """Cached wrapper — avoids hitting cache-lookup overhead for repeated calls."""
    gt_lang = GOOGLE_LANG_MAP.get(target, target)
    try:
        return _get_trans().translate(text, gt_lang)
    except Exception:
        return text


def tr_gui(text_key, lang="en"):
    """Translate a GUI text key — tries dict first, then dynamic."""
    if lang == "en":
        return GUI_TEXT["en"].get(text_key, text_key)
    lang_map = GUI_TEXT.get(lang)
    if lang_map and text_key in lang_map:
        return lang_map[text_key]
    en_text = GUI_TEXT["en"].get(text_key, text_key)
    return _cached_translate(en_text, lang)


def tr_parent(parent_key, lang="en"):
    """Translate a legend parent category."""
    if lang == "en":
        return PARENT_CLASSES["en"].get(parent_key, parent_key)
    lang_map = PARENT_CLASSES.get(lang)
    if lang_map and parent_key in lang_map:
        return lang_map[parent_key]
    en_text = PARENT_CLASSES["en"].get(parent_key, parent_key)
    return _cached_translate(en_text, lang)


def tr_header(lang="en"):
    """Get table headers for language — tries dict first, then dynamic."""
    if lang == "en":
        return list(TABLE_HEADERS["en"])
    lang_map = TABLE_HEADERS.get(lang)
    if lang_map:
        return list(lang_map)
    return _cached_translate("\n".join(TABLE_HEADERS["en"]), lang).split("\n")


def get_ocr_lang(lang="en"):
    """Get easyocr language list for the selected UI language."""
    return OCR_LANG.get(lang, OCR_LANG["en"])


def prewarm_language(lang: str) -> None:
    """Pre-translate all known strings into *lang* via batch API.

    Call this once when the user switches language — after this every
    tr_*() call for that language is instant (cache hit).  This avoids
    hundreds of individual API calls when populating detection results.
    """
    if lang == "en" or lang not in GOOGLE_LANG_MAP:
        return

    gt_lang = GOOGLE_LANG_MAP.get(lang, lang)
    trans = _get_trans()

    # collect all unique English source texts
    unique_texts: set[str] = set()

    # class names (English display values)
    for v in CLASS_NAMES["en"].values():
        unique_texts.add(v)

    # GUI texts
    for v in GUI_TEXT["en"].values():
        unique_texts.add(v)

    # parent categories
    for v in PARENT_CLASSES["en"].values():
        unique_texts.add(v)

    # table headers
    for v in TABLE_HEADERS["en"]:
        unique_texts.add(v)

    text_list = sorted(unique_texts)  # deterministic order
    trans.prewarm(text_list, gt_lang)


def available_language_count() -> int:
    """Number of languages available in the UI dropdown."""
    return len(SUPPORTED_LANGUAGES)
