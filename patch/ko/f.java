package gvl;

import java.io.InputStream;
import java.util.Vector;
import javax.microedition.lcdui.Font;
import javax.microedition.lcdui.Graphics;

public final class f {
    int a;
    byte[][] b;
    byte[][] c;
    private static Vector d;
    private static Graphics e;
    private static byte f;
    private static byte g;
    private static String h;
    private static int i;
    private static Font koreanFont;

    public f(String path, byte ignored, byte lineHeight, byte baseline) {
        d = new Vector();
        f = lineHeight;
        g = baseline;
        b(path);
        h = "";

        // 9 virtual pixels is large enough to stay readable after the 176x208
        // canvas is scaled to a Galaxy S10, while still fitting NOM 2's compact
        // menu/dialog boxes. Font AA is enabled by the launcher profile.
        try {
            koreanFont = new Font(0, 0, -1, 9.0f);
        } catch (Throwable t) {
            try {
                koreanFont = Font.getFont(0, 0, 8);
            } catch (Throwable ignored2) {
                koreanFont = Font.getDefaultFont();
            }
        }
    }

    public static void a(Graphics graphics) {
        e = graphics;
    }

    public static byte a() { return f; }
    public static byte b() { return g; }

    private static boolean isNativeChar(char ch) {
        return ch > 126;
    }

    private static int asciiGlyph(char ch) {
        if (ch >= 'A' && ch <= 'Z') return 32 + (ch - 'A');
        if (ch >= 'a' && ch <= 'z') return 64 + (ch - 'a');
        if (ch >= '0' && ch <= '9') return 15 + (ch - '0');
        switch (ch) {
            case '!': return 0; case '"': return 1; case '#': return 2; case '$': return 3;
            case '%': return 4; case '&': return 5; case '\'': return 6; case '(': return 7;
            case ')': return 8; case '*': return 9; case '+': return 10; case ',': return 11;
            case '-': return 12; case '.': return 13; case '/': return 14; case ':': return 25;
            case ';': return 26; case '<': return 27; case '=': return 28; case '>': return 29;
            case '?': return 30; case '@': return 31; case '[': return 58; case ']': return 60;
            case '^': return 61; case '_': return 62; case '`': return 63; case '{': return 90;
            case '|': return 91; case '}': return 92; case '~': return 93; case ' ': return 99;
            default: return 100;
        }
    }

    private static int asciiWidth(char ch) {
        switch (ch) {
            case 'f': case 'k': return 4;
            case 'i': return 1;
            case 'j': case 't': case 'I': return 3;
            case 'l': case 'J': return 4;
            case '.': return 1;
            case ',': case ':': return 2;
            default: return 5;
        }
    }

    private static int charWidth(char ch) {
        if (isNativeChar(ch) && koreanFont != null) {
            try {
                int w = koreanFont.charWidth(ch);
                return Math.max(7, Math.min(10, w));
            } catch (Throwable ignored) {
                return 9;
            }
        }
        return asciiWidth(ch);
    }

    public final int a(String text) {
        if (text == null || text.length() == 0) return 0;
        int width = 0;
        boolean joined = false;
        for (int p = 0; p < text.length(); p++) {
            char ch = text.charAt(p);
            if (ch == ' ') {
                width += charWidth(ch);
                joined = false;
            } else {
                width += charWidth(ch) + (joined ? 1 : 0);
                joined = true;
            }
        }
        return width;
    }

    private void drawLine(String text, int x, int y) {
        if (text == null || e == null) return;
        int cursor = 0;
        boolean joined = false;
        Font previous = null;
        try { previous = e.getFont(); } catch (Throwable ignored) {}

        for (int p = 0; p < text.length(); p++) {
            char ch = text.charAt(p);
            if (p > 0) {
                char prev = text.charAt(p - 1);
                if (prev == ' ') cursor += charWidth(prev);
                else cursor += charWidth(prev) + (joined ? 1 : 0);
            }
            joined = ch != ' ';

            if (ch == ' ') continue;
            if (isNativeChar(ch)) {
                try {
                    if (koreanFont != null) e.setFont(koreanFont);
                    e.drawString(String.valueOf(ch), x + cursor, y - 1, 20);
                } catch (Throwable ignored) {
                    drawGlyph(asciiGlyph('?'), x + cursor, y);
                }
            } else {
                drawGlyph(asciiGlyph(ch), x + cursor, y);
            }
        }

        try { if (previous != null) e.setFont(previous); } catch (Throwable ignored) {}
    }

    private int split(String text, int maxWidth) {
        d.removeAllElements();
        if (text == null || text.length() == 0) {
            d.addElement("");
            i = 1;
            return 1;
        }

        int start = 0;
        while (start <= text.length()) {
            int pipe = text.indexOf('|', start);
            String segment = pipe >= 0 ? text.substring(start, pipe) : text.substring(start);
            wrapSegment(segment, maxWidth);
            if (pipe < 0) break;
            start = pipe + 1;
            if (start == text.length()) d.addElement("");
        }
        i = d.size();
        return i;
    }

    private void wrapSegment(String segment, int maxWidth) {
        if (maxWidth <= 0 || a(segment) <= maxWidth) {
            d.addElement(segment);
            return;
        }
        int start = 0;
        while (start < segment.length()) {
            int best = start + 1;
            int lastSpace = -1;
            for (int end = start + 1; end <= segment.length(); end++) {
                String part = segment.substring(start, end);
                if (a(part) > maxWidth) break;
                best = end;
                if (segment.charAt(end - 1) == ' ') lastSpace = end - 1;
            }
            int cut = best;
            if (best < segment.length() && lastSpace >= start) cut = lastSpace;
            if (cut <= start) cut = Math.min(segment.length(), start + 1);
            String line = segment.substring(start, cut);
            while (line.endsWith(" ")) line = line.substring(0, line.length() - 1);
            d.addElement(line);
            start = cut;
            while (start < segment.length() && segment.charAt(start) == ' ') start++;
        }
    }

    public final int a(String text, int x, int y, int maxWidth, int lineStep, int anchor) {
        int lines = split(text, maxWidth);
        for (int line = 0; line < lines; line++) {
            String value = (String) d.elementAt(line);
            int lineWidth = a(value);
            int drawX = x;
            if (anchor == 17) drawX = x - lineWidth / 2;
            else if (anchor == 18) drawX = x - lineWidth;
            drawLine(value, drawX, y + line * lineStep);
        }
        return lines;
    }

    private void b(String path) {
        try {
            InputStream in = getClass().getResourceAsStream(path);
            if (in == null) return;
            a = ((in.read() & 255) << 8) | (in.read() & 255);
            int rectCount = ((in.read() & 255) << 8) | (in.read() & 255);
            b = new byte[2][a + 1];
            c = new byte[4][rectCount];
            readFully(in, b[0]);
            readFully(in, b[1]);
            readFully(in, c[0]);
            readFully(in, c[1]);
            readFully(in, c[2]);
            readFully(in, c[3]);
            in.close();
        } catch (Throwable ignored) {
        }
    }

    private static void readFully(InputStream in, byte[] out) throws java.io.IOException {
        int off = 0;
        while (off < out.length) {
            int count = in.read(out, off, out.length - off);
            if (count < 0) throw new java.io.IOException("Unexpected EOF");
            off += count;
        }
    }

    private void drawGlyph(int glyph, int x, int y) {
        if (e == null || b == null || c == null || glyph < 0 || glyph >= a) return;
        int first = ((b[0][glyph] & 255) << 8) | (b[1][glyph] & 255);
        int last = ((b[0][glyph + 1] & 255) << 8) | (b[1][glyph + 1] & 255);
        for (int r = first; r < last; r++) {
            e.fillRect(x + c[0][r], y + c[1][r], c[2][r], c[3][r]);
        }
    }
}
