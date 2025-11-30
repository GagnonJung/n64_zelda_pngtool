# -*- coding: utf-8 -*-
import sys, os, re, json
from PyQt5 import QtWidgets, QtGui, QtCore
from PIL import Image, ImageDraw, ImageFont

APP_TITLE = "Zelda Text Tool 1.00 — Safe Tags + Bold + Pixel Mode Fix"
CONFIG_FILE = "zelda_text_tool_config.json"

# =========================================================
# Config helpers
# =========================================================
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# =========================================================
# Text / Tag helpers
# =========================================================

# 모든 <> 태그를 잘라내기 위한 범용 스플릿
TAG_SPLIT = re.compile(r'(<[^>]+>)')

def parse_tokens(text: str):
    """일반 문자열과 <태그> 를 분리해서 리스트로 반환."""
    if not text:
        return []
    parts = TAG_SPLIT.split(text)
    return [p for p in parts if p != ""]

def get_font(path: str, size: int):
    base = path or "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(base, int(size))

# -------------------- Measure line --------------------
def measure_line(draw, text, base_size, font_paths, stretch=1.0):
    """태그를 해석해서 한 줄의 폭/높이만 계산 (볼드/그림자는 폭에 영향 X)."""
    f1, f2 = font_paths
    cur_font_path = f1 or "C:/Windows/Fonts/malgun.ttf"
    cur_size = base_size
    cur_stretch = stretch
    cur_font = get_font(cur_font_path, cur_size)

    total_w = 0
    max_h = 0

    for tk in parse_tokens(text):
        # 태그 처리
        if tk.startswith("<") and tk.endswith(">"):
            tag = tk[1:-1].strip().lower()

            if tag.startswith("size"):
                m = re.findall(r"\d+", tag)
                if m:
                    cur_size = int(m[0])
                    cur_font = get_font(cur_font_path, cur_size)
                continue

            if tag == "/size":
                cur_size = base_size
                cur_font = get_font(cur_font_path, cur_size)
                continue

            if tag.startswith("font"):
                m = re.findall(r"\d+", tag)
                if m and m[0] == "2":
                    cur_font_path = f2 or cur_font_path
                else:
                    cur_font_path = f1 or cur_font_path
                cur_font = get_font(cur_font_path, cur_size)
                continue

            if tag == "/font":
                cur_font_path = f1 or cur_font_path
                cur_font = get_font(cur_font_path, cur_size)
                continue

            if tag.startswith("stretch"):
                m = re.findall(r"[0-9.]+", tag)
                if m:
                    try:
                        cur_stretch = float(m[0])
                    except ValueError:
                        cur_stretch = stretch
                continue

            if tag == "/stretch":
                cur_stretch = stretch
                continue

            # <bold>, </bold> 는 폭에 영향 없음
            continue

        # 실제 텍스트
        if not tk:
            continue
        x0, y0, x1, y1 = draw.textbbox((0, 0), tk, font=cur_font)
        w = int((x1 - x0) * cur_stretch)
        h = y1 - y0
        total_w += w
        max_h = max(max_h, h)

    if max_h == 0:
        x0, y0, x1, y1 = draw.textbbox((0, 0), "A", font=get_font(cur_font_path, base_size))
        max_h = y1 - y0
    return total_w, max_h

# -------------------- Render line --------------------
def render_line(draw, text, base_size, font_paths,
                x, y, fill, outline_px, outline_color,
                shadow, px_mode, stretch=1.0,
                bold_px=0):
    """
    한 줄 렌더링.
    - px_mode: 픽셀 폰트 모드 (1비트 렌더)
    - bold_px: 굵게 채우기 반경(px)
    - shadow: (dx, dy, color) or None
    - stretch: 장평 (x축 스케일)
    """
    f1, f2 = font_paths
    cur_font_path = f1 or "C:/Windows/Fonts/malgun.ttf"
    cur_size = base_size
    cur_stretch = stretch
    cur_font = get_font(cur_font_path, cur_size)

    cursor_x = x
    tokens = parse_tokens(text)

    # 전역 bold 여부 (슬라이더 값이 0이면 기본은 False)
    default_bold_on = bold_px > 0
    bold_on = default_bold_on

    def glyph_from_text(tok: str):
        """현재 폰트 설정으로 tok를 렌더한 grayscale glyph와 원본 크기 반환."""
        if not tok:
            return None, 0, 0
        mask = cur_font.getmask(tok, mode="L")
        w, h = mask.size
        if w == 0 or h == 0:
            return None, w, h
        img = Image.new("L", (w, h))
        img.putdata(list(mask))
        return img, w, h

    for tk in tokens:
        # ---------------- 태그 처리 ----------------
        if tk.startswith("<") and tk.endswith(">"):
            tag = tk[1:-1].strip().lower()

            if tag.startswith("size"):
                m = re.findall(r"\d+", tag)
                if m:
                    cur_size = int(m[0])
                    cur_font = get_font(cur_font_path, cur_size)
                continue

            if tag == "/size":
                cur_size = base_size
                cur_font = get_font(cur_font_path, cur_size)
                continue

            if tag.startswith("font"):
                m = re.findall(r"\d+", tag)
                if m and m[0] == "2":
                    cur_font_path = f2 or cur_font_path
                else:
                    cur_font_path = f1 or cur_font_path
                cur_font = get_font(cur_font_path, cur_size)
                continue

            if tag == "/font":
                cur_font_path = f1 or cur_font_path
                cur_font = get_font(cur_font_path, cur_size)
                continue

            if tag.startswith("stretch"):
                m = re.findall(r"[0-9.]+", tag)
                if m:
                    try:
                        cur_stretch = float(m[0])
                    except ValueError:
                        cur_stretch = stretch
                continue

            if tag == "/stretch":
                cur_stretch = stretch
                continue

            if tag == "bold":
                bold_on = True
                continue

            if tag == "/bold":
                bold_on = default_bold_on
                continue

            # 알 수 없는 태그는 무시
            continue

        # ---------------- 실제 텍스트 ----------------
        if not tk:
            continue

        effective_bold = bold_px if bold_on and bold_px > 0 else 0

        # 공통: glyph 생성 + stretch 적용
        glyph, w0, h0 = glyph_from_text(tk)
        if glyph is None or w0 == 0 or h0 == 0:
            continue

        new_w = max(1, int(w0 * cur_stretch))

        if px_mode:
            # ===== 픽셀(1비트) 렌더 =====
            glyph_scaled = glyph.resize((new_w, h0), Image.NEAREST)
            glyph_bw = glyph_scaled.point(lambda v: 255 if v > 127 else 0, mode="1")

            # 그림자
            if shadow is not None:
                dx, dy, scol = shadow
                draw.bitmap((cursor_x + dx, y + dy), glyph_bw, scol)

            # 외곽선
            if outline_px > 0:
                for ox in range(-outline_px, outline_px + 1):
                    for oy in range(-outline_px, outline_px + 1):
                        if ox == 0 and oy == 0:
                            continue
                        draw.bitmap((cursor_x + ox, y + oy), glyph_bw, outline_color)

            # 볼드
            if effective_bold > 0:
                for bx in range(-effective_bold, effective_bold + 1):
                    for by in range(-effective_bold, effective_bold + 1):
                        if bx == 0 and by == 0:
                            continue
                        draw.bitmap((cursor_x + bx, y + by), glyph_bw, fill)

            # 본문
            draw.bitmap((cursor_x, y), glyph_bw, fill)
            cursor_x += new_w
            continue

        # ===== 일반(AA) 렌더 =====
        glyph_scaled = glyph.resize((new_w, h0), Image.BILINEAR)

        # 그림자
        if shadow is not None:
            dx, dy, scol = shadow
            draw.bitmap((cursor_x + dx, y + dy), glyph_scaled, scol)

        # 외곽선
        if outline_px > 0:
            for ox in range(-outline_px, outline_px + 1):
                for oy in range(-outline_px, outline_px + 1):
                    if ox == 0 and oy == 0:
                        continue
                    draw.bitmap((cursor_x + ox, y + oy), glyph_scaled, outline_color)

        # 볼드
        if effective_bold > 0:
            for bx in range(-effective_bold, effective_bold + 1):
                for by in range(-effective_bold, effective_bold + 1):
                    if bx == 0 and by == 0:
                        continue
                    draw.bitmap((cursor_x + bx, y + by), glyph_scaled, fill)

        # 본문
        draw.bitmap((cursor_x, y), glyph_scaled, fill)
        cursor_x += new_w


# =========================================================
# 메인 위젯
# =========================================================
class ZeldaTextTool(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1280, 760)
        self.cfg = load_config()

        self.font1_path = self.cfg.get("font1_path", "")
        self.font2_path = self.cfg.get("font2_path", "")
        self.text_color = tuple(self.cfg.get("text_color", (255, 255, 255)))
        self.outline_color = tuple(self.cfg.get("outline_color", (0, 0, 0)))
        self.shadow_color = tuple(self.cfg.get("shadow_color", (0, 0, 0)))

        self.shadow_dir = self.cfg.get("shadow_dir", "우하")
        self.shadow_px = int(self.cfg.get("shadow_px", 1))
        self.bold_px = int(self.cfg.get("bold_px", 0))

        self.image_list = []
        self.current_index = -1
        self.image_path = None
        self.image_size = (512, 128)

        self._build_ui()
        self._restore_settings()

    # -----------------------------------------------------
    # UI
    # -----------------------------------------------------
    def _build_ui(self):
        main = QtWidgets.QVBoxLayout(self)
        row = QtWidgets.QHBoxLayout()
        main.addLayout(row, 1)

        # -------- 좌측 컨트롤 --------
        left = QtWidgets.QVBoxLayout()
        row.addLayout(left, 1)

        left.addWidget(QtWidgets.QLabel("텍스트 입력"))
        self.text_edit = QtWidgets.QTextEdit()
        left.addWidget(self.text_edit)

        # 폰트 라벨
        self.lbl_font1 = QtWidgets.QLabel(
            f"폰트1: {os.path.basename(self.font1_path) if self.font1_path else '(없음)'}")
        self.lbl_font2 = QtWidgets.QLabel(
            f"폰트2: {os.path.basename(self.font2_path) if self.font2_path else '(없음)'}")
        self.lbl_font1.setStyleSheet("color:#aaccff;")
        self.lbl_font2.setStyleSheet("color:#aaccff;")
        left.addWidget(self.lbl_font1)
        left.addWidget(self.lbl_font2)

        form = QtWidgets.QFormLayout()
        self.spin_size = QtWidgets.QSpinBox(); self.spin_size.setRange(6, 128)
        self.spin_outline = QtWidgets.QSpinBox(); self.spin_outline.setRange(0, 8)
        self.spin_bold = QtWidgets.QSpinBox(); self.spin_bold.setRange(0, 5)
        self.dbl_scale_x = QtWidgets.QDoubleSpinBox(); self.dbl_scale_x.setRange(0.5, 3.0); self.dbl_scale_x.setSingleStep(0.05)
        self.dbl_line = QtWidgets.QDoubleSpinBox(); self.dbl_line.setRange(0.2, 3.0); self.dbl_line.setSingleStep(0.05)
        self.combo_align = QtWidgets.QComboBox(); self.combo_align.addItems(["왼쪽", "가운데", "오른쪽"])
        self.spin_offx = QtWidgets.QSpinBox(); self.spin_offx.setRange(-128, 128)
        self.spin_offy = QtWidgets.QSpinBox(); self.spin_offy.setRange(-128, 128)

        self.chk_shadow = QtWidgets.QCheckBox("그림자 사용")
        self.combo_shadow_dir = QtWidgets.QComboBox()
        self.combo_shadow_dir.addItems(["없음","좌상","상","우상","좌","중앙","우","좌하","하","우하"])
        self.spin_shadow_px = QtWidgets.QSpinBox(); self.spin_shadow_px.setRange(0, 8)

        form.addRow("폰트 크기", self.spin_size)
        form.addRow("테두리 두께(px)", self.spin_outline)
        form.addRow("볼드 강도(px)", self.spin_bold)
        form.addRow("폰트 장평", self.dbl_scale_x)
        form.addRow("행간 배율", self.dbl_line)
        form.addRow("정렬 방식", self.combo_align)
        form.addRow("X 오프셋", self.spin_offx)
        form.addRow("Y 오프셋", self.spin_offy)
        form.addRow(self.chk_shadow, None)
        form.addRow("그림자 방향", self.combo_shadow_dir)
        form.addRow("그림자 강도(px)", self.spin_shadow_px)
        left.addLayout(form)

        # 모드 체크박스
        self.chk_pixel = QtWidgets.QCheckBox("픽셀 폰트 모드 (안티앨리어싱 없음)")
        self.chk_boss = QtWidgets.QCheckBox("보스 카드 모드 (상단만 편집)")
        left.addWidget(self.chk_pixel)
        left.addWidget(self.chk_boss)

        # 버튼들
        for text, fn in [
            ("폰트1 선택 (Ctrl+F)", self.pick_font1),
            ("폰트2 선택 (Ctrl+Shift+F)", self.pick_font2),
            ("글자색", self.pick_text_color),
            ("테두리색", self.pick_outline_color),
            ("그림자색", self.pick_shadow_color),
        ]:
            b = QtWidgets.QPushButton(text)
            b.clicked.connect(fn)
            left.addWidget(b)

        self.btn_save = QtWidgets.QPushButton("저장 (Ctrl+S)")
        self.btn_open = QtWidgets.QPushButton("원본 불러오기 (Ctrl+O)")
        self.btn_save.clicked.connect(self.save_image)
        self.btn_open.clicked.connect(lambda: self.load_image())
        left.addWidget(self.btn_save)
        left.addWidget(self.btn_open)
        left.addStretch(1)

        # -------- 미리보기 / 원본 --------
        self.lbl_left = QtWidgets.QLabel("미리보기")
        self.lbl_left.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_left.setStyleSheet("background:#222; color:#888;")
        row.addWidget(self.lbl_left, 2)

        self.lbl_right = QtWidgets.QLabel("원본 미리보기")
        self.lbl_right.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_right.setStyleSheet("background:#222; color:#888;")
        row.addWidget(self.lbl_right, 2)

        # 상태바
        self.status = QtWidgets.QLabel("이미지: 0 / 0")
        self.status.setAlignment(QtCore.Qt.AlignCenter)
        self.status.setStyleSheet("background:#111;color:#8f8;font-weight:bold;padding:4px;")
        main.addWidget(self.status)

        # 이벤트 연결
        self.text_edit.textChanged.connect(self.update_preview)
        for w in (self.spin_size, self.spin_outline, self.spin_bold,
                  self.dbl_scale_x, self.dbl_line,
                  self.spin_offx, self.spin_offy,
                  self.spin_shadow_px):
            w.valueChanged.connect(self.update_preview)

        self.combo_align.currentTextChanged.connect(self.update_preview)
        self.combo_shadow_dir.currentTextChanged.connect(self.update_preview)
        self.chk_pixel.stateChanged.connect(self.update_preview)
        self.chk_boss.stateChanged.connect(self.update_preview)
        self.chk_shadow.stateChanged.connect(self.update_preview)

        # 단축키
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, activated=self.save_image)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+O"), self, activated=lambda: self.load_image())
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+F"), self, activated=self.pick_font1)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Shift+F"), self, activated=self.pick_font2)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Left), self, activated=self.prev_image)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Right), self, activated=self.next_image)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_PageUp), self, activated=self.prev_image)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_PageDown), self, activated=self.next_image)

        # 휠로 이미지 전환
        def _wheel_nav(e):
            if e.angleDelta().y() > 0:
                self.prev_image()
            else:
                self.next_image()
        self.lbl_left.wheelEvent = _wheel_nav

    # -----------------------------------------------------
    # Settings
    # -----------------------------------------------------
    def _restore_settings(self):
        c = self.cfg
        self.spin_size.setValue(c.get("font_size", 12))
        self.spin_outline.setValue(c.get("outline", 2))
        self.spin_bold.setValue(c.get("bold_px", self.bold_px))
        self.dbl_scale_x.setValue(c.get("scale_x", 1.0))
        self.dbl_line.setValue(c.get("line_spacing", 1.0))
        self.combo_align.setCurrentText(c.get("align", "가운데"))
        self.spin_offx.setValue(c.get("offx", 0))
        self.spin_offy.setValue(c.get("offy", 0))
        self.chk_pixel.setChecked(bool(c.get("pixel_mode", False)))
        self.chk_boss.setChecked(bool(c.get("boss_mode", True)))
        self.chk_shadow.setChecked(bool(c.get("shadow_on", True)))
        self.combo_shadow_dir.setCurrentText(c.get("shadow_dir", self.shadow_dir))
        self.spin_shadow_px.setValue(int(c.get("shadow_px", self.shadow_px)))

    def _save_settings(self):
        self.cfg.update({
            "font1_path": self.font1_path,
            "font2_path": self.font2_path,
            "font_size": self.spin_size.value(),
            "outline": self.spin_outline.value(),
            "bold_px": self.spin_bold.value(),
            "scale_x": self.dbl_scale_x.value(),
            "line_spacing": self.dbl_line.value(),
            "align": self.combo_align.currentText(),
            "offx": self.spin_offx.value(),
            "offy": self.spin_offy.value(),
            "pixel_mode": self.chk_pixel.isChecked(),
            "boss_mode": self.chk_boss.isChecked(),
            "text_color": self.text_color,
            "outline_color": self.outline_color,
            "shadow_color": self.shadow_color,
            "shadow_on": self.chk_shadow.isChecked(),
            "shadow_dir": self.combo_shadow_dir.currentText(),
            "shadow_px": self.spin_shadow_px.value(),
        })
        save_config(self.cfg)

    def closeEvent(self, e):
        self._save_settings()
        e.accept()

    # -----------------------------------------------------
    # Font / color pickers
    # -----------------------------------------------------
    def pick_font1(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "폰트1 선택", "", "Font Files (*.ttf *.otf)")
        if p:
            self.font1_path = p
            self.lbl_font1.setText(f"폰트1: {os.path.basename(p)}")
            self.update_preview()

    def pick_font2(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "폰트2 선택", "", "Font Files (*.ttf *.otf)")
        if p:
            self.font2_path = p
            self.lbl_font2.setText(f"폰트2: {os.path.basename(p)}")
            self.update_preview()

    def pick_text_color(self):
        c = QtWidgets.QColorDialog.getColor()
        if c.isValid():
            self.text_color = c.getRgb()[:3]
            self.update_preview()

    def pick_outline_color(self):
        c = QtWidgets.QColorDialog.getColor()
        if c.isValid():
            self.outline_color = c.getRgb()[:3]
            self.update_preview()

    def pick_shadow_color(self):
        c = QtWidgets.QColorDialog.getColor()
        if c.isValid():
            self.shadow_color = c.getRgb()[:3]
            self.update_preview()

    # -----------------------------------------------------
    # Image navigation
    # -----------------------------------------------------
    def load_image(self, path=None):
        if not path:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "원본 이미지 불러오기", "", "PNG Files (*.png)")
            if not path:
                return
        folder = os.path.dirname(path)
        self.image_list = sorted(
            [os.path.join(folder, f) for f in os.listdir(folder)
             if f.lower().endswith(".png")]
        )
        try:
            self.current_index = self.image_list.index(path)
        except ValueError:
            self.current_index = 0
        self.image_path = self.image_list[self.current_index]
        self._display_original()
        self.update_preview()

    def _display_original(self):
        if not self.image_path:
            return
        im = Image.open(self.image_path).convert("RGBA")
        self.image_size = im.size
        pix = QtGui.QPixmap(self.image_path).scaled(
            self.lbl_right.width(), self.lbl_right.height(),
            QtCore.Qt.KeepAspectRatio)
        self.lbl_right.setPixmap(pix)
        self._update_status()

    def _update_status(self):
        total = len(self.image_list)
        cur = self.current_index + 1 if total else 0
        w, h = self.image_size
        mark = ""
        if total > 0:
            cur_path = self.image_list[self.current_index]
            out = os.path.join(os.path.dirname(cur_path), "output",
                               os.path.basename(cur_path))
            mark = " ✅" if os.path.exists(out) else " ·"
        self.status.setText(f"이미지: {cur} / {total} ({w}×{h}){mark}")

    def next_image(self, step=1):
        if not self.image_list:
            return
        self.current_index = (self.current_index + step) % len(self.image_list)
        self.image_path = self.image_list[self.current_index]
        self._display_original()
        self.update_preview()

    def prev_image(self):
        self.next_image(-1)

    # -----------------------------------------------------
    # Shadow helper
    # -----------------------------------------------------
    def _shadow_vector(self, px):
        table = {
            "없음": (0, 0),
            "좌상": (-px, -px), "상": (0, -px), "우상": (px, -px),
            "좌": (-px, 0),     "중앙": (0, 0),  "우": (px, 0),
            "좌하": (-px, px),  "하": (0, px),  "우하": (px, px),
        }
        return table.get(self.combo_shadow_dir.currentText(), (px, px))

    # -----------------------------------------------------
    # Compose preview
    # -----------------------------------------------------
    def _compose_preview(self, W, H):
        txt = self.text_edit.toPlainText().strip()
        if not txt:
            return Image.new("RGBA", (W, H), (0, 0, 0, 0))

        px_mode = self.chk_pixel.isChecked()
        SCALE = 4 if px_mode else 1
        cw, ch = W * SCALE, H * SCALE

        canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        base_size = int(self.spin_size.value()) * SCALE
        line_mul = self.dbl_line.value()
        outline = self.spin_outline.value()
        bold_px = self.spin_bold.value()
        scale_x = self.dbl_scale_x.value()
        offx = self.spin_offx.value() * SCALE
        offy = self.spin_offy.value() * SCALE
        align = self.combo_align.currentText()
        color = self.text_color

        # 그림자
        shadow_tuple = None
        if self.chk_shadow.isChecked():
            spx = max(0, int(self.spin_shadow_px.value())) * SCALE
            dx, dy = self._shadow_vector(spx)
            if dx != 0 or dy != 0:
                shadow_tuple = (dx, dy, self.shadow_color)

        # 줄 폭/높이 계산
        lines = txt.split("\n")
        widths, heights = [], []
        for ln in lines:
            w, h = measure_line(draw, ln, base_size,
                                (self.font1_path, self.font2_path),
                                stretch=scale_x)
            widths.append(w)
            heights.append(h)
        total_h = sum(heights) * line_mul if heights else 0

        cx = (cw // 2) + offx
        cy = (ch // 2) + offy
        y_cursor = cy - int(total_h // 2)

        for i, ln in enumerate(lines):
            lw, lh = widths[i], heights[i]
            if align == "왼쪽":
                lx = cx - (cw // 2) + (5 * SCALE)
            elif align == "오른쪽":
                lx = cx + (cw // 2) - lw - (5 * SCALE)
            else:
                lx = cx - (lw // 2)

            render_line(
                draw, ln, base_size,
                (self.font1_path, self.font2_path),
                lx, y_cursor,
                fill=color,
                outline_px=outline,
                outline_color=self.outline_color,
                shadow=shadow_tuple,
                px_mode=px_mode,
                stretch=scale_x,
                bold_px=bold_px,
            )
            y_cursor += int(lh * line_mul)

        canvas = canvas.resize((W, H), Image.NEAREST if px_mode else Image.BILINEAR)

        # 보스 카드 모드: 상단만 덮어쓰기
        if self.chk_boss.isChecked() and self.image_path and os.path.exists(self.image_path):
            base = Image.open(self.image_path).convert("RGBA").copy()
            top_h = H // 2
            merged = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            merged.paste(canvas.crop((0, 0, W, top_h)), (0, 0))
            merged.paste(base.crop((0, top_h, W, H)), (0, top_h))
            return merged

        return canvas

    def update_preview(self):
        W, H = self.image_size
        if W <= 0 or H <= 0:
            W, H = (512, 128)
        im = self._compose_preview(W, H)
        qim = QtGui.QImage(im.tobytes("raw", "RGBA"), W, H,
                           QtGui.QImage.Format_RGBA8888)
        self.lbl_left.setPixmap(
            QtGui.QPixmap.fromImage(qim).scaled(
                self.lbl_left.width(), self.lbl_left.height(),
                QtCore.Qt.KeepAspectRatio
            )
        )
        self._update_status()

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------
    def save_image(self):
        if not self.image_list or self.current_index < 0:
            QtWidgets.QMessageBox.warning(self, "경고", "이미지를 먼저 불러오세요.")
            return

        cur_path = self.image_list[self.current_index]
        out_dir = os.path.join(os.path.dirname(cur_path), "output")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, os.path.basename(cur_path))

        W, H = self.image_size
        final = self._compose_preview(W, H)
        final.save(out_path, "PNG")
        QtWidgets.QMessageBox.information(self, "저장 완료", f"저장됨: {out_path}")
        self._update_status()

# =========================================================
# main
# =========================================================
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    app.setFont(QtGui.QFont("Malgun Gothic"))

    w = ZeldaTextTool()
    w.show()
    sys.exit(app.exec_())
