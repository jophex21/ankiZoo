(function () {
    let DATA = null;
    let catalogById = {};
    let blinkOn = false;
    let prevCoins = null;

    function rebuildCatalogIndex() {
        catalogById = {};
        DATA.catalog.forEach((a) => { catalogById[a.id] = a; });
    }

    // The coin sprite as an inline <img> for any innerHTML context (falls back to
    // the coin emoji if the sprite didn't ship). Native title tooltips can't show
    // an image, so anything mentioning coins uses data-tip (setupTooltip) instead.
    function coinImg() {
        return DATA.coinUri ? `<img class="az-coin-icon" src="${DATA.coinUri}" alt="coins">` : '\u{1FA99}';
    }

    // ---------- Toasts ----------
    function showToast(message, isError) {
        if (!message) return;
        const container = document.getElementById('az-toast-container');
        const el = document.createElement('div');
        el.className = 'az-toast' + (isError ? ' error' : '');
        el.textContent = message;
        container.appendChild(el);
        requestAnimationFrame(() => el.classList.add('show'));
        setTimeout(() => {
            el.classList.remove('show');
            setTimeout(() => el.remove(), 250);
        }, 3000);
    }

    // ---------- Modal ----------
    function closeModal() {
        document.getElementById('az-modal-overlay').classList.remove('show');
        const modal = document.getElementById('az-modal');
        modal.classList.remove('az-case-modal');
        modal.innerHTML = '';
    }

    function openPlaceAnimalModal(plotId) {
        const placedIds = new Set(Object.values(DATA.plotAnimals));
        const available = DATA.ownedAnimals.filter((id) => !placedIds.has(id));
        const modal = document.getElementById('az-modal');
        if (available.length === 0) {
            modal.innerHTML = '<h3>No animals available</h3><p>Unlock an animal in the Skill Tree tab, then buy it with coins.</p>' +
                '<button class="az-modal-close">Close</button>';
        } else {
            const items = available.map((id) => {
                const a = catalogById[id];
                return `<div class="az-modal-animal-item" data-animal-id="${id}">
                    <img src="${a.sprite_idle_uri}">
                    <span>${a.name}</span>
                </div>`;
            }).join('');
            modal.innerHTML = `<h3>Place an animal</h3><div class="az-modal-animal-list">${items}</div>
                <button class="az-modal-close">Cancel</button>`;
            modal.querySelectorAll('.az-modal-animal-item').forEach((el) => {
                el.addEventListener('click', () => {
                    const animalId = el.dataset.animalId;
                    pycmd(`placeAnimal:${plotId}|${animalId}`);
                    closeModal();
                });
            });
        }
        modal.querySelector('.az-modal-close').addEventListener('click', closeModal);
        document.getElementById('az-modal-overlay').classList.add('show');
    }

    function openManageTileModal(plotId, animalId) {
        const a = catalogById[animalId];
        const modal = document.getElementById('az-modal');
        modal.innerHTML = `<h3>${a.name}</h3>
            <img src="${a.sprite_idle_uri}" style="width:64px;height:64px;image-rendering:pixelated;display:block;margin:0 auto 10px;">
            <button class="az-modal-remove">Return to collection</button>
            <button class="az-modal-close">Close</button>`;
        modal.querySelector('.az-modal-remove').addEventListener('click', () => {
            pycmd(`removeAnimal:${plotId}`);
            closeModal();
        });
        modal.querySelector('.az-modal-close').addEventListener('click', closeModal);
        document.getElementById('az-modal-overlay').classList.add('show');
    }

    // ---------- Loot box (CS:GO-style case opening) ----------
    const CASE_ITEM_W = 96;   // tile width incl. the 8px gap
    const CASE_WIN_IDX = 48;  // where the winning tile sits in the strip
    const CASE_STRIP_LEN = 56;

    // Fill the strip's inner icon + rarity border for any reward-shaped object.
    function fillCaseItem(el, reward) {
        const color = (DATA.rarityColors || {})[reward.rarity] || '#9aa0a6';
        el.style.setProperty('--rarity', color);
        const icon = document.createElement('div');
        icon.className = 'az-case-icon';
        if (reward.kind === 'animal') {
            const a = catalogById[reward.animal_id];
            if (a) {
                const img = document.createElement('img');
                img.src = a.sprite_idle_uri;
                icon.appendChild(img);
            } else { icon.textContent = '\u{1F43E}'; }
        } else if (reward.kind === 'skill') {
            icon.textContent = '✦';
        } else {
            icon.innerHTML = coinImg();
        }
        el.appendChild(icon);
        const label = document.createElement('div');
        label.className = 'az-case-item-label';
        label.textContent = reward.kind === 'coins' ? `${reward.amount}`
            : reward.kind === 'skill' ? `${reward.amount} SP` : reward.label;
        el.appendChild(label);
    }

    // A random cosmetic reward for the decoy tiles the strip scrolls past.
    function randomDecoy() {
        const bands = Object.keys(DATA.rarityColors || { common: 1 });
        const rarity = bands[Math.floor(Math.random() * bands.length)] || 'common';
        const roll = Math.random();
        if (roll < 0.25 && DATA.catalog.length) {
            const a = DATA.catalog[Math.floor(Math.random() * DATA.catalog.length)];
            return { kind: 'animal', animal_id: a.id, rarity, label: a.name };
        }
        if (roll < 0.32) return { kind: 'skill', amount: 1 + Math.floor(Math.random() * 2), rarity };
        return { kind: 'coins', amount: (2 + Math.floor(Math.random() * 80)) * 5, rarity };
    }

    function openCaseModal(reward) {
        const modal = document.getElementById('az-modal');
        modal.classList.add('az-case-modal');
        modal.innerHTML = `<h3>Opening loot box...</h3>
            <div class="az-case">
                <div class="az-case-marker"></div>
                <div class="az-case-viewport"><div class="az-case-strip" id="az-case-strip"></div></div>
            </div>
            <div class="az-case-result" id="az-case-result"></div>`;
        const strip = modal.querySelector('#az-case-strip');

        // Build the reel: decoys everywhere, the real reward at the landing slot.
        for (let i = 0; i < CASE_STRIP_LEN; i++) {
            const item = document.createElement('div');
            item.className = 'az-case-item';
            fillCaseItem(item, i === CASE_WIN_IDX ? reward : randomDecoy());
            strip.appendChild(item);
        }

        document.getElementById('az-modal-overlay').classList.add('show');

        // Center the winning tile under the marker, with a little jitter so it
        // doesn't always stop dead-center.
        const viewportW = modal.querySelector('.az-case-viewport').clientWidth;
        const jitter = Math.round((Math.random() - 0.5) * (CASE_ITEM_W * 0.5));
        const offset = CASE_WIN_IDX * CASE_ITEM_W + CASE_ITEM_W / 2 - viewportW / 2 + jitter;

        strip.style.transform = 'translateX(0)';
        // Force reflow so the transition runs from the initial position.
        void strip.offsetWidth;
        strip.style.transition = 'transform 5.6s cubic-bezier(0.12, 0.82, 0.16, 1)';
        strip.style.transform = `translateX(${-offset}px)`;

        const finish = () => {
            strip.removeEventListener('transitionend', finish);
            const winEl = strip.children[CASE_WIN_IDX];
            if (winEl) winEl.classList.add('win');
            const rarityLabel = (DATA.rarityLabels || {})[reward.rarity] || '';
            const color = (DATA.rarityColors || {})[reward.rarity] || '#9aa0a6';
            const result = document.getElementById('az-case-result');
            result.style.setProperty('--rarity', color);
            result.innerHTML = `<div class="az-case-rarity">${rarityLabel}</div>
                <div class="az-case-prize">${caseResultText(reward)}</div>
                <button class="az-modal-close">Collect</button>`;
            result.classList.add('show');
            modal.querySelector('h3').textContent = 'You won!';
            result.querySelector('.az-modal-close').addEventListener('click', closeModal);
        };
        strip.addEventListener('transitionend', finish);
    }

    function caseResultText(reward) {
        if (reward.kind === 'coins') return `${coinImg()} ${reward.amount} coins`;
        if (reward.kind === 'skill') return `✦ ${reward.label}`;
        if (reward.kind === 'animal') return `\u{1F43E} ${reward.label} joined your zoo!`;
        return reward.label || '';
    }

    // ---------- Settings ----------
    function openResetConfirmModal() {
        const modal = document.getElementById('az-modal');
        modal.innerHTML = `<h3>Reset all progress?</h3>
            <p>This will permanently erase your XP, coins, unlocked animals, zoo layout, and quests. This cannot be undone.</p>
            <button class="az-modal-remove" id="az-reset-confirm">Reset Everything</button>
            <button class="az-modal-close">Cancel</button>`;
        modal.querySelector('#az-reset-confirm').addEventListener('click', () => {
            pycmd('resetZoo');
            closeModal();
        });
        modal.querySelector('.az-modal-close').addEventListener('click', closeModal);
        document.getElementById('az-modal-overlay').classList.add('show');
    }

    function renderColorPickers() {
        Object.keys(DATA.widgetColors || {}).forEach((key) => {
            const hexInput = document.getElementById(`az-color-${key}-hex`);
            const swatchBtn = document.getElementById(`az-color-${key}-swatch`);
            const value = DATA.widgetColors[key];
            if (hexInput) hexInput.value = value;
            if (swatchBtn) swatchBtn.style.backgroundColor = value;
        });
    }

    function renderReviewerToggles() {
        Object.entries(DATA.reviewerToggles || {}).forEach(([key, on]) => {
            const box = document.getElementById(`az-toggle-${key}`);
            if (box) box.checked = on;
        });
    }

    function setupReviewerToggles() {
        Object.keys(DATA.reviewerToggles || {}).forEach((key) => {
            const box = document.getElementById(`az-toggle-${key}`);
            if (box) box.addEventListener('change', () => pycmd(`setReviewerToggle:${key}:${box.checked ? 1 : 0}`));
        });
        renderReviewerToggles();
    }

    // Reviewer appearance rows are generated from DATA.reviewerStyle.schema
    // (config.REVIEWER_STYLE) so new knobs only need adding in Python.
    const STYLE_HEX_RE = /^(#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?)?$/;
    function sendStyle(req) { pycmd('reviewerStyle:' + JSON.stringify(req)); }

    function buildStyleRow(field) {
        const row = document.createElement('div');
        row.className = 'az-color-row';
        const label = document.createElement('span');
        label.className = 'az-color-label';
        label.textContent = field.label;
        row.appendChild(label);
        let input;
        if (field.kind === 'choice') {
            input = document.createElement('select');
            input.className = 'az-color-hex az-select';
            field.extra.forEach(([value, text]) => input.add(new Option(text, value)));
            row.appendChild(input);
        } else if (field.kind === 'int') {
            const [min, max, unit] = field.extra;
            input = document.createElement('input');
            Object.assign(input, { type: 'number', min, max, step: 1, className: 'az-color-hex' });
            const unitEl = document.createElement('span');
            unitEl.className = 'az-style-unit';
            unitEl.textContent = unit;
            row.append(input, unitEl);
        } else {
            input = document.createElement('input');
            Object.assign(input, { type: 'text', className: 'az-color-hex', placeholder: 'Theme default' });
            input.title = '#RRGGBB, or #RRGGBBAA for transparency. Leave blank to follow Anki\'s theme.';
            const swatch = document.createElement('button');
            swatch.type = 'button';
            swatch.className = 'az-color-swatch';
            swatch.dataset.swatchFor = field.key;
            swatch.addEventListener('click', () => sendStyle({ action: 'pick', key: field.key }));
            row.append(input, swatch);
        }
        input.dataset.styleKey = field.key;
        input.addEventListener('change', () => {
            if (field.kind === 'color' && !STYLE_HEX_RE.test(input.value.trim())) {
                showToast('Use #RRGGBB or #RRGGBBAA (or leave blank).', true);
                return;
            }
            if (field.kind === 'int' && input.value === '') return;
            sendStyle({ action: 'set', key: field.key, value: field.kind === 'int' ? Number(input.value) : input.value.trim() });
        });
        return row;
    }

    function renderReviewerStyle() {
        const st = DATA.reviewerStyle;
        if (!st) return;
        document.querySelectorAll('[data-style-key]').forEach((input) => {
            if (document.activeElement !== input) input.value = st.values[input.dataset.styleKey];
        });
        document.querySelectorAll('[data-swatch-for]').forEach((sw) => {
            const value = st.values[sw.dataset.swatchFor];
            sw.style.background = value || '';
            sw.classList.toggle('az-swatch-theme', !value);
        });
        // Live-apply Zoo-window colors; 'initial' makes var() use its fallback (theme/default).
        st.schema.filter((f) => f.group === 'zoo').forEach((f) => {
            const v = st.values[f.key];
            const css = f.kind === 'int' ? (f.extra[2] === '%' ? v / 100 : v + f.extra[2]) : (v || 'initial');
            document.documentElement.style.setProperty(`--az-${f.key}`, css);
        });
        const minutes = document.getElementById('az-pomo-minutes');
        if (minutes && document.activeElement !== minutes) minutes.value = DATA.pomodoroMinutes;
        const select = document.getElementById('az-preset-select');
        if (select) {
            const prev = select.value;
            select.innerHTML = '';
            if (!st.presets.length) select.add(new Option('No saved presets', ''));
            st.presets.forEach((name) => select.add(new Option(name, name)));
            if (st.presets.includes(prev)) select.value = prev;
        }
    }

    function openStyleResetModal() {
        const modal = document.getElementById('az-modal');
        modal.innerHTML = `<h3>Reset appearance?</h3>
            <p>The Zoo window, Pomodoro timer and reviewer header go back to their default look. Saved presets are kept.</p>
            <button class="az-modal-remove" id="az-style-reset-confirm">Reset</button>
            <button class="az-modal-close">Cancel</button>`;
        modal.querySelector('#az-style-reset-confirm').addEventListener('click', () => {
            sendStyle({ action: 'reset' });
            closeModal();
        });
        modal.querySelector('.az-modal-close').addEventListener('click', closeModal);
        document.getElementById('az-modal-overlay').classList.add('show');
    }

    function setupReviewerStyle() {
        const st = DATA.reviewerStyle;
        if (!st) return;
        st.schema.forEach((field) => {
            const host = document.getElementById(`az-style-rows-${field.group}`);
            if (host) host.appendChild(buildStyleRow(field));
        });
        const minutes = document.getElementById('az-pomo-minutes');
        minutes.addEventListener('change', () => {
            if (minutes.value !== '') pycmd(`setPomodoroMinutes:${minutes.value}`);
        });
        const nameInput = document.getElementById('az-preset-name');
        document.getElementById('az-preset-save').addEventListener('click', () => {
            sendStyle({ action: 'savePreset', name: nameInput.value });
            nameInput.value = '';
        });
        const select = document.getElementById('az-preset-select');
        document.getElementById('az-preset-load').addEventListener('click', () => {
            if (select.value) sendStyle({ action: 'loadPreset', name: select.value });
        });
        document.getElementById('az-preset-delete').addEventListener('click', () => {
            if (select.value) sendStyle({ action: 'deletePreset', name: select.value });
        });
        document.getElementById('az-style-reset').addEventListener('click', openStyleResetModal);
        renderReviewerStyle();
    }

    // One floating tooltip for every [data-tip] element (HTML allowed, unlike title).
    function setupTooltip() {
        const tip = document.createElement('div');
        tip.className = 'az-tip';
        document.body.appendChild(tip);
        let current = null;
        const place = (e) => {
            const pad = 8;
            let x = e.clientX + 14, y = e.clientY + 16;
            if (x + tip.offsetWidth + pad > window.innerWidth) x = e.clientX - tip.offsetWidth - 10;
            if (y + tip.offsetHeight + pad > window.innerHeight) y = e.clientY - tip.offsetHeight - 10;
            tip.style.left = Math.max(pad, x) + 'px';
            tip.style.top = Math.max(pad, y) + 'px';
        };
        document.addEventListener('mouseover', (e) => {
            const el = e.target.closest && e.target.closest('[data-tip]');
            if (el === current) return;
            current = el;
            tip.classList.toggle('show', !!el);
            if (el) { tip.innerHTML = el.dataset.tip; place(e); }
        });
        document.addEventListener('mousemove', (e) => { if (current) place(e); });
    }

    function setupColorPickers() {
        const HEX_RE = /^#[0-9a-fA-F]{6}$/;
        Object.keys(DATA.widgetColors || {}).forEach((key) => {
            const hexInput = document.getElementById(`az-color-${key}-hex`);
            const swatchBtn = document.getElementById(`az-color-${key}-swatch`);
            if (!hexInput || !swatchBtn) return;

            // The swatch opens Qt's native QColorDialog (via pickWidgetColor) rather than
            // an HTML <input type="color">, which was returning inaccurate colors on macOS
            // (it goes through Chromium's own color picker/management, not the real OS panel).
            swatchBtn.addEventListener('click', () => pycmd(`pickWidgetColor:${key}`));
            hexInput.addEventListener('change', () => {
                if (!HEX_RE.test(hexInput.value)) return;
                pycmd(`setWidgetColor:${key}:${hexInput.value}`);
            });
        });
        renderColorPickers();
    }

    // ---------- Header ----------
    function renderRankBadge() {
        const badge = document.getElementById('az-header-badge');
        if (!badge) return;
        if (!DATA.rankBadgeUri) { badge.style.display = 'none'; return; }
        badge.style.display = '';
        badge.style.backgroundImage = `url(${DATA.rankBadgeUri})`;
        // The sheet is a cols x rows grid read left-to-right, top-to-bottom, so
        // cell index N is level N+1. Clamp to the last badge past max level.
        const cols = DATA.rankBadgeCols || 10;
        const rows = DATA.rankBadgeRows || 5;
        const idx = Math.max(0, Math.min(cols * rows - 1, DATA.level - 1));
        const col = idx % cols;
        const row = Math.floor(idx / cols);
        const px = cols > 1 ? (col / (cols - 1)) * 100 : 0;
        const py = rows > 1 ? (row / (rows - 1)) * 100 : 0;
        badge.style.backgroundPosition = `${px}% ${py}%`;
        badge.title = `${DATA.rank} (Lv. ${DATA.level})`;
    }

    function renderHeader() {
        document.getElementById('az-header-rank').textContent = DATA.rank;
        document.getElementById('az-header-level').textContent = 'Lv. ' + DATA.level;
        renderRankBadge();
        const pct = DATA.xpToNextLevel > 0 ? Math.min(100, (DATA.xpIntoLevel / DATA.xpToNextLevel) * 100) : 100;
        document.getElementById('az-header-xp-fill').style.width = pct + '%';
        document.getElementById('az-header-xp-label').textContent =
            DATA.xpToNextLevel > 0 ? `${DATA.xpIntoLevel} / ${DATA.xpToNextLevel} XP` : 'Max level';
        const skillEl = document.getElementById('az-header-skill');
        if (skillEl) skillEl.textContent = DATA.skillPoints != null ? DATA.skillPoints : 0;
        const coinsEl = document.getElementById('az-header-coins');
        if (prevCoins !== null && DATA.coins > prevCoins) {
            coinsEl.classList.remove('az-coin-pop');
            void coinsEl.offsetWidth;  // restart the pulse animation
            coinsEl.classList.add('az-coin-pop');
        }
        coinsEl.innerHTML = coinImg() + DATA.coins;
        prevCoins = DATA.coins;
    }

    // ---------- Zoo map ----------
    // The park is one big scrollable canvas: biome districts (each a block of
    // square plots that grows with its animal count) ringed around a central
    // shops plaza, joined by curved paths. Plots fill left-to-right per district.
    // The canvas is deliberately kept near the stage's own aspect (~1.65:1). fitScale()
    // takes the SMALLER of the width/height ratios, so a tall canvas in a wide stage
    // fits on height alone and everything renders tiny -- wide districts avoid that.
    const MAP_W = 1740, MAP_H = 946;
    const TILE = 62, PITCH = 68, D_COLS = 7;         // district grid, 6px between plots
    const PLAZA_COLS = 5, PLAZA_ROWS = 4;            // 20 building slots
    const SVG_NS = 'http://www.w3.org/2000/svg';
    // Top-left anchor of each district's plot grid, keyed by biome name. Districts ring
    // the plaza in three columns, and the bottom-left is left open on purpose -- that's
    // where the map key floats, and it must not cover a district at the fit view.
    // ponytail: hand-placed so nothing collides at the current catalog size --
    // districts grow downward, so re-check spacing when a biome gains animals.
    const DISTRICT_ANCHORS = {
        Arctic:  { x: 70, y: 70 },   Ocean:  { x: 70, y: 272 },
        Savanna: { x: 612, y: 70 },  Forest: { x: 612, y: 678 },
        Jungle:  { x: 1154, y: 70 }, 'Desert & Outback': { x: 1154, y: 408 },
    };
    const PLAZA_CENTER = { x: 847, y: 473 };
    // ponytail: hand-scattered into the bands between parcels, clear of the creek.
    // Re-check against the district extents if any anchor above moves.
    const TREES = [[300, 28], [850, 28], [1400, 28],
                   [28, 300], [28, 700], [28, 900],
                   [1220, 700], [1380, 640], [1520, 760], [1280, 880], [1450, 890],
                   [1180, 900], [1600, 620],
                   [480, 620], [520, 900], [300, 910],
                   [620, 918], [900, 918], [1080, 918], [1350, 918]];
    const TREE_SVG =
        '<svg viewBox="0 0 46 52" xmlns="http://www.w3.org/2000/svg">' +
        '<ellipse cx="23" cy="48" rx="13" ry="3" fill="rgba(42,53,36,0.18)"/>' +
        '<path d="M22 46v-9h4v9z" fill="#6d5233"/>' +
        '<path d="M24 4 36 24H12z" fill="#4a9450"/>' +
        '<path d="M24 14 39 39H9z" fill="#3c8244"/>' +
        '<path d="M24 4 36 24h-12z" fill="rgba(0,0,0,0.10)"/>' +
        '<path d="M24 14 39 39H24z" fill="rgba(0,0,0,0.10)"/>' +
        '</svg>';

    let mapScale = 1, mapTx = 0, mapTy = 0, mapFitted = false;

    function biomeCounts() {
        const counts = {};
        DATA.catalog.forEach((a) => { counts[a.biome] = (counts[a.biome] || 0) + 1; });
        return counts;
    }

    function svgEl(name, attrs) {
        const el = document.createElementNS(SVG_NS, name);
        Object.keys(attrs).forEach((k) => el.setAttribute(k, attrs[k]));
        return el;
    }

    // A gentle curve from a to b (perpendicular nudge on the control point).
    function curvePath(ax, ay, bx, by) {
        const mx = (ax + bx) / 2, my = (ay + by) / 2;
        const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy) || 1;
        return `M${ax},${ay} Q${mx - (dy / len) * 30},${my + (dx / len) * 30} ${bx},${by}`;
    }

    function makePlot(cx, cy) {
        const el = document.createElement('div');
        el.className = 'az-plot';
        el.style.left = cx + 'px';
        el.style.top = cy + 'px';
        return el;
    }

    function renderDistrict(canvas, biome, count) {
        const anchor = DISTRICT_ANCHORS[biome];
        if (!anchor) return;
        const color = (DATA.biomeColors || {})[biome] || '#8aa66a';
        const rows = Math.max(1, Math.ceil(count / D_COLS));
        const usedCols = Math.min(count, D_COLS);
        const w = (usedCols - 1) * PITCH + TILE, h = (rows - 1) * PITCH + TILE;

        const panel = document.createElement('div');
        panel.className = 'az-district';
        panel.style.left = (anchor.x - 14) + 'px';
        panel.style.top = (anchor.y - 14) + 'px';
        panel.style.width = (w + 28) + 'px';
        panel.style.height = (h + 28) + 'px';
        // lighter wash than a UI card, plus a fine survey hatch so parcels differ in
        // texture as well as hue (the border comes from .az-district in CSS)
        panel.style.background =
            `repeating-linear-gradient(45deg, ${hexA(color, 0.16)} 0 3px, transparent 3px 7px), ` +
            `linear-gradient(160deg, ${hexA(color, 0.34)}, ${hexA(color, 0.16)})`;
        let placed = 0;
        for (let i = 0; i < count; i++) if (DATA.plotAnimals[`${biome}-${i}`]) placed++;
        panel.innerHTML = `<span class="az-sign">${biome}</span><span class="az-count">${placed}/${count}</span>`;
        canvas.appendChild(panel);

        const unlockedSet = new Set(DATA.unlockedPlots || []);
        let unlockedInBiome = 0;
        for (let i = 0; i < count; i++) if (unlockedSet.has(`${biome}-${i}`)) unlockedInBiome++;

        for (let i = 0; i < count; i++) {
            const plotId = `${biome}-${i}`;
            const col = i % D_COLS, row = Math.floor(i / D_COLS);
            const cx = anchor.x + col * PITCH + TILE / 2;
            const cy = anchor.y + row * PITCH + TILE / 2;
            const el = makePlot(cx, cy);
            const animalId = DATA.plotAnimals[plotId];

            if (animalId && catalogById[animalId]) {
                el.classList.add('az-plot-exhibit');
                const terr = DATA.terrainImages[biome];
                if (terr) {
                    // Terrain lives in its own layer so it can be blurred without the sprite.
                    const wrap = document.createElement('div');
                    wrap.className = 'az-plot-bg-wrap';
                    const bg = document.createElement('div');
                    bg.className = 'az-plot-bg';
                    bg.style.backgroundImage = `url(${terr.uri})`;
                    wrap.appendChild(bg);
                    el.appendChild(wrap);
                } else el.style.background = hexA(color, 0.85);
                const a = catalogById[animalId];
                const img = document.createElement('img');
                img.className = 'az-sprite';
                img.dataset.idleUri = a.sprite_idle_uri;
                img.dataset.blinkUri = a.sprite_blink_uri || a.sprite_idle_uri;
                img.src = img.dataset.idleUri;
                el.appendChild(img);
                el.title = a.name;
                el.addEventListener('click', () => openManageTileModal(plotId, animalId));
            } else if (i < unlockedInBiome) {
                el.classList.add('az-plot-tape');
                el.title = 'Empty enclosure -- place an animal';
                el.addEventListener('click', () => openPlaceAnimalModal(plotId));
            } else if (i === unlockedInBiome) {
                el.classList.add('az-plot-buyable');
                el.title = `Clear this plot: ${DATA.nextPlotCost} coins`;
                const cost = document.createElement('div');
                cost.className = 'az-plot-cost';
                cost.innerHTML = coinImg() + DATA.nextPlotCost;
                el.appendChild(cost);
                el.addEventListener('click', () => pycmd(`unlockPlot:${plotId}`));
            } else {
                el.classList.add('az-plot-locked');
            }
            canvas.appendChild(el);
        }
    }

    function renderPlaza(canvas) {
        const cols = PLAZA_COLS, rows = PLAZA_ROWS;
        const w = (cols - 1) * PITCH + TILE, h = (rows - 1) * PITCH + TILE;
        const ax = PLAZA_CENTER.x - w / 2, ay = PLAZA_CENTER.y - h / 2;
        const panel = document.createElement('div');
        panel.className = 'az-district';
        panel.style.left = (ax - 14) + 'px';
        panel.style.top = (ay - 14) + 'px';
        panel.style.width = (w + 28) + 'px';
        panel.style.height = (h + 28) + 'px';
        panel.style.background =
            'repeating-linear-gradient(45deg, rgba(140,106,68,0.10) 0 3px, transparent 3px 7px), ' +
            'linear-gradient(160deg, rgba(228,220,198,0.8), rgba(210,200,170,0.55))';
        panel.innerHTML = '<span class="az-sign">Plaza</span><span class="az-count">Shops</span>';
        canvas.appendChild(panel);

        const total = DATA.buildingSlots || 20;
        for (let i = 0; i < total; i++) {
            const col = i % cols, row = Math.floor(i / cols);
            const el = makePlot(ax + col * PITCH + TILE / 2, ay + row * PITCH + TILE / 2);
            el.classList.add('az-plot-soon');
            el.style.setProperty('--awn', ['#c96f5a', '#5d8fa8', '#c9a24a'][i % 3]);
            el.title = 'Shops are coming soon';
            el.addEventListener('click', () => showToast('Shops are coming soon!', false));
            canvas.appendChild(el);
        }
    }

    // The legend lives outside #az-map-canvas (renderMap wipes that), so it's
    // refreshed by hand on every state push.
    function renderMapKey(counts) {
        const tally = document.getElementById('az-map-tally');
        if (tally) {
            const total = Object.keys(counts).reduce((n, b) => n + counts[b], 0);
            let open = 0;
            Object.keys(DATA.plotAnimals || {}).forEach((id) => { if (DATA.plotAnimals[id]) open++; });
            tally.textContent = `${open} of ${total} enclosures open`;
        }
        const cost = document.getElementById('az-map-key-cost');
        if (cost) cost.innerHTML = 'For sale &middot; ' + coinImg() + DATA.nextPlotCost;
    }

    function renderMap() {
        const canvas = document.getElementById('az-map-canvas');
        if (!canvas) return;
        canvas.innerHTML = '';
        canvas.style.width = MAP_W + 'px';
        canvas.style.height = MAP_H + 'px';

        const grounds = document.createElement('div');
        grounds.className = 'az-map-grounds';
        canvas.appendChild(grounds);

        // creek down the right edge
        const creek = svgEl('svg', { class: 'az-map-creek', width: MAP_W, height: MAP_H, viewBox: `0 0 ${MAP_W} ${MAP_H}`, preserveAspectRatio: 'none' });
        const creekD = 'M1694,10 C1712,180 1676,340 1698,500 C1716,670 1680,820 1696,940';
        creek.appendChild(svgEl('path', { d: creekD, fill: 'none', stroke: '#6cc0dd', 'stroke-width': 46, 'stroke-linecap': 'round' }));
        creek.appendChild(svgEl('path', { d: creekD, fill: 'none', stroke: '#a9e2f2', 'stroke-width': 20, 'stroke-linecap': 'round' }));
        canvas.appendChild(creek);

        // paths radiating from the plaza to each district
        const order = DATA.biomeOrder || Object.keys(DISTRICT_ANCHORS);
        const counts = biomeCounts();
        const paths = svgEl('svg', { class: 'az-map-paths', width: MAP_W, height: MAP_H, viewBox: `0 0 ${MAP_W} ${MAP_H}`, preserveAspectRatio: 'none' });
        order.forEach((biome) => {
            const anchor = DISTRICT_ANCHORS[biome];
            if (!anchor) return;
            const n = counts[biome] || 0;
            const rows = Math.max(1, Math.ceil(n / D_COLS));
            const usedCols = Math.min(Math.max(n, 1), D_COLS);
            const dcx = anchor.x + ((usedCols - 1) * PITCH + TILE) / 2;
            const dcy = anchor.y + ((rows - 1) * PITCH + TILE) / 2;
            const d = curvePath(PLAZA_CENTER.x, PLAZA_CENTER.y, dcx, dcy);
            paths.appendChild(svgEl('path', { d, fill: 'none', stroke: '#c9bd9c', 'stroke-width': 26, 'stroke-linecap': 'round' }));
            paths.appendChild(svgEl('path', { d, fill: 'none', stroke: '#e9e1cc', 'stroke-width': 15, 'stroke-linecap': 'round' }));
        });
        canvas.appendChild(paths);

        TREES.forEach(([x, y], i) => {
            const t = document.createElement('div');
            t.className = 'az-map-tree';
            t.style.left = x + 'px';
            t.style.top = y + 'px';
            // vary the cluster so a scatter of one drawing doesn't read as a stamp
            const s = 0.72 + (i % 4) * 0.14;
            t.style.transform = `translate(-50%,-50%) scale(${s}) scaleX(${i % 3 ? 1 : -1})`;
            t.innerHTML = TREE_SVG;
            canvas.appendChild(t);
        });

        order.forEach((biome) => renderDistrict(canvas, biome, counts[biome] || 0));
        renderPlaza(canvas);
        renderMapKey(counts);

        if (!mapFitted) fitMap();
        else applyMapTransform();
    }

    // rgba() from a #rrggbb hex and alpha.
    function hexA(hex, a) {
        const n = parseInt(hex.slice(1), 16);
        return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
    }

    // ---------- Map pan + zoom ----------
    function applyMapTransform() {
        const canvas = document.getElementById('az-map-canvas');
        if (canvas) canvas.style.transform = `translate(${mapTx}px,${mapTy}px) scale(${mapScale})`;
    }
    function fitScale() {
        const stage = document.getElementById('az-stage');
        if (!stage || !stage.clientWidth) return 0.5;
        return Math.min(stage.clientWidth / MAP_W, stage.clientHeight / MAP_H);
    }
    function clampMap() {
        const stage = document.getElementById('az-stage');
        if (!stage) return;
        const vw = stage.clientWidth, vh = stage.clientHeight;
        mapTx = MAP_W * mapScale < vw ? (vw - MAP_W * mapScale) / 2 : Math.min(0, Math.max(vw - MAP_W * mapScale, mapTx));
        mapTy = MAP_H * mapScale < vh ? (vh - MAP_H * mapScale) / 2 : Math.min(0, Math.max(vh - MAP_H * mapScale, mapTy));
    }
    function fitMap() {
        const stage = document.getElementById('az-stage');
        if (!stage || !stage.clientWidth) return;
        mapScale = fitScale();
        mapTx = (stage.clientWidth - MAP_W * mapScale) / 2;
        mapTy = (stage.clientHeight - MAP_H * mapScale) / 2;
        mapFitted = true;
        applyMapTransform();
    }
    // Sprites are pixel art (image-rendering: pixelated), so they stay crisp up close.
    const MAP_MAX_ZOOM = 4;
    function zoomMapAt(px, py, next) {
        const min = fitScale();
        next = Math.max(min, Math.min(MAP_MAX_ZOOM, next));
        mapTx = px - (px - mapTx) * (next / mapScale);
        mapTy = py - (py - mapTy) * (next / mapScale);
        mapScale = next;
        clampMap();
        applyMapTransform();
    }
    function setupMapControls() {
        const stage = document.getElementById('az-stage');
        if (!stage || stage.dataset.wired) return;
        stage.dataset.wired = '1';
        stage.addEventListener('wheel', (e) => {
            e.preventDefault();
            const r = stage.getBoundingClientRect();
            zoomMapAt(e.clientX - r.left, e.clientY - r.top, mapScale * (e.deltaY < 0 ? 1.12 : 0.9));
        }, { passive: false });
        let drag = null;
        stage.addEventListener('pointerdown', (e) => {
            if (e.target.closest('.az-plot, .az-map-key')) { drag = null; return; }
            drag = { x: e.clientX, y: e.clientY, tx: mapTx, ty: mapTy };
            try { stage.setPointerCapture(e.pointerId); } catch (_) {}
        });
        stage.addEventListener('pointermove', (e) => {
            if (!drag) return;
            mapTx = drag.tx + (e.clientX - drag.x);
            mapTy = drag.ty + (e.clientY - drag.y);
            clampMap();
            applyMapTransform();
        });
        const endDrag = () => { drag = null; };
        stage.addEventListener('pointerup', endDrag);
        stage.addEventListener('pointercancel', endDrag);
        const hud = (id, fn) => { const b = document.getElementById(id); if (b) b.addEventListener('click', fn); };
        hud('az-map-fit', fitMap);
        hud('az-map-in', () => zoomMapAt(stage.clientWidth / 2, stage.clientHeight / 2, mapScale * 1.25));
        hud('az-map-out', () => zoomMapAt(stage.clientWidth / 2, stage.clientHeight / 2, mapScale * 0.8));
    }

    // ---------- Skill Tree ----------
    const NODE_R = 30;          // node radius (px)
    const COL_W = 152;          // horizontal spacing between biome trunks
    const ROW_H = 80;           // vertical spacing between slots up a trunk
    const OFF = 40;             // how far a sibling animal branches off the trunk
    const ROOT_GAP = 78;        // gap from the root up to a trunk's first slot
    const PAD_X = 40, PAD_TOP = 74, PAD_BOT = 70;

    // Build each biome as a trunk of IUCN tiers (LC at the bottom, CR at the top).
    // Animals of a tier branch off to alternating sides; a gate marker sits on the
    // trunk below each tier showing the ★ needed to reach it. Returns geometry.
    function layoutTree() {
        const order = DATA.biomeOrder && DATA.biomeOrder.length
            ? DATA.biomeOrder
            : Array.from(new Set(DATA.catalog.map((a) => a.biome)));
        const biomes = order.map((biome) => {
            const members = DATA.catalog.filter((a) => a.biome === biome);
            if (!members.length) return null;
            // Distinct tiers present, ordered by tier_rank.
            const tiers = [];
            members.forEach((a) => {
                let t = tiers.find((x) => x.tier === a.conservation);
                if (!t) {
                    t = { tier: a.conservation, name: a.tier_name, threshold: a.tier_threshold, rank: a.tier_rank, minLevel: a.min_level || 0, animals: [] };
                    tiers.push(t);
                }
                t.animals.push(a);
            });
            tiers.sort((x, y) => x.rank - y.rank);
            tiers.forEach((t) => t.animals.sort((x, y) => x.within_tier_index - y.within_tier_index));
            // Assign slots bottom -> top: a gate below each tier (except the first),
            // then that tier's animals (alternating sides if there's more than one).
            let slot = 0;
            tiers.forEach((t, ti) => {
                if (ti > 0) { t.gateSlot = slot; slot += 1; }
                t.animals.forEach((a, j) => {
                    a._slot = slot;
                    a._side = t.animals.length > 1 ? (j % 2 === 0 ? -1 : 1) : 0;
                    slot += 1;
                });
            });
            return { biome, color: members[0].biome_color, tiers, slots: slot, members };
        }).filter(Boolean);

        const maxSlots = Math.max(1, ...biomes.map((b) => b.slots));
        const baseY = PAD_TOP + (maxSlots - 1) * ROW_H;   // y of slot 0 (nearest root)
        const rootY = baseY + ROOT_GAP;
        const width = PAD_X * 2 + 2 * NODE_R + (biomes.length - 1) * COL_W;
        const height = rootY + NODE_R + PAD_BOT;
        const slotY = (s) => baseY - s * ROW_H;
        biomes.forEach((b, bi) => { b.x = PAD_X + NODE_R + bi * COL_W; b.topY = slotY(b.slots - 1); });
        return { biomes, root: { x: width / 2, y: rootY }, width, height, slotY };
    }

    // Node states:
    //   owned     -> bought & placeable in the zoo
    //   buyable   -> unlocked & affordable: click to buy with coins (🪙 cost)
    //   buypoor   -> unlocked but can't afford the coin price yet (🪙 cost)
    //   ready     -> tier open & enough skill points: click to unlock (✦ cost)
    //   avail     -> tier open but not enough skill points (dim, ✦ cost)
    //   tierlocked-> its tier isn't reachable yet (silhouette, 🔒, ★ requirement)
    function nodeState(a, unlockedSet, ownedSet, stars) {
        if (ownedSet.has(a.id)) return 'owned';
        if (unlockedSet.has(a.id)) return DATA.coins >= a.cost_coins ? 'buyable' : 'buypoor';
        const accessible = (stars[a.biome] || 0) >= a.tier_threshold && (DATA.level || 0) >= (a.min_level || 0);
        if (!accessible) return 'tierlocked';
        return DATA.skillPoints >= a.skill_cost ? 'ready' : 'avail';
    }

    function renderTree() {
        const tree = document.getElementById('az-tree');
        tree.innerHTML = '';
        const unlockedSet = new Set(DATA.unlockedAnimals || []);
        const ownedSet = new Set(DATA.ownedAnimals);
        const stars = DATA.biomeStars || {};
        const L = layoutTree();
        tree.style.width = L.width + 'px';
        tree.style.height = L.height + 'px';

        // --- SVG connector layer: root fan, biome trunks, animal stubs ---
        const svgNS = 'http://www.w3.org/2000/svg';
        const svg = document.createElementNS(svgNS, 'svg');
        svg.setAttribute('class', 'az-tree-svg');
        svg.setAttribute('width', L.width);
        svg.setAttribute('height', L.height);
        svg.setAttribute('viewBox', `0 0 ${L.width} ${L.height}`);
        function line(x1, y1, x2, y2, color, w, op) {
            const el = document.createElementNS(svgNS, 'line');
            el.setAttribute('x1', x1); el.setAttribute('y1', y1);
            el.setAttribute('x2', x2); el.setAttribute('y2', y2);
            el.setAttribute('stroke', color); el.setAttribute('stroke-width', w);
            el.setAttribute('stroke-linecap', 'round'); el.setAttribute('opacity', op);
            svg.appendChild(el);
        }
        L.biomes.forEach((b) => {
            line(L.root.x, L.root.y, b.x, L.root.y, b.color, 5, 0.3);   // fan from root
            line(b.x, L.root.y, b.x, b.topY, b.color, 5, 0.32);         // trunk
            b.tiers.forEach((t) => t.animals.forEach((a) => {
                if (a._side !== 0) line(b.x, L.slotY(a._slot), b.x + a._side * OFF, L.slotY(a._slot), b.color, 4, unlockedSet.has(a.id) ? 0.9 : 0.3);
            }));
        });
        tree.appendChild(svg);

        // --- Root node ---
        const root = document.createElement('div');
        root.className = 'az-node az-node-root';
        root.style.left = (L.root.x - NODE_R) + 'px';
        root.style.top = (L.root.y - NODE_R) + 'px';
        root.innerHTML = '<span class="az-node-root-icon">\u{1F43E}</span>';
        root.title = 'Your zoo';
        tree.appendChild(root);

        L.biomes.forEach((b) => {
            // Biome header with live star total
            const head = document.createElement('div');
            head.className = 'az-biome-head';
            head.style.left = b.x + 'px';
            head.style.top = (b.topY - ROW_H * 0.72) + 'px';
            head.style.setProperty('--biome-color', b.color);
            head.innerHTML = `${b.biome} <b>★${stars[b.biome] || 0}</b>`;
            tree.appendChild(head);

            // Tier gate markers on the trunk
            b.tiers.forEach((t) => {
                if (t.gateSlot == null) return;
                const starsOk = (stars[b.biome] || 0) >= t.threshold;
                const levelOk = (DATA.level || 0) >= (t.minLevel || 0);
                const passed = starsOk && levelOk;
                const gate = document.createElement('div');
                gate.className = 'az-gate' + (passed ? ' open' : ' closed');
                gate.style.left = b.x + 'px';
                gate.style.top = L.slotY(t.gateSlot) + 'px';
                gate.style.setProperty('--biome-color', b.color);
                gate.innerHTML = t.minLevel
                    ? `★${t.threshold} <span>${t.tier} · Lvl ${t.minLevel}</span>`
                    : `★${t.threshold} <span>${t.tier}</span>`;
                if (passed) {
                    gate.title = `${t.name} unlocked`;
                } else if (!levelOk) {
                    gate.title = `Reach level ${t.minLevel} to reach ${t.name} in ${b.biome}`;
                } else {
                    gate.title = `Earn ${t.threshold}★ in ${b.biome} to reach ${t.name}`;
                }
                tree.appendChild(gate);
            });

            // Animal nodes
            b.tiers.forEach((t) => t.animals.forEach((a) => {
                const x = b.x + a._side * OFF, y = L.slotY(a._slot);
                const state = nodeState(a, unlockedSet, ownedSet, stars);
                const node = document.createElement('div');
                node.className = 'az-node az-node-' + state;
                node.style.left = (x - NODE_R) + 'px';
                node.style.top = (y - NODE_R) + 'px';
                node.style.setProperty('--biome-color', a.biome_color);
                const known = state !== 'tierlocked';
                node.dataset.tip = `${a.name} — ${a.tier_name} (worth ★${a.star_value})<br>`
                    + `Unlock: ✦${a.skill_cost} skill pts &nbsp; Buy: ${coinImg()}${a.cost_coins} coins`;

                const img = document.createElement('img');
                img.className = 'az-node-sprite';
                img.dataset.idleUri = a.sprite_idle_uri;
                img.dataset.blinkUri = a.sprite_blink_uri || a.sprite_idle_uri;
                img.src = img.dataset.idleUri;
                node.appendChild(img);

                if (state === 'tierlocked') {
                    const lock = document.createElement('span');
                    lock.className = 'az-node-lock';
                    lock.textContent = '\u{1F512}';
                    node.appendChild(lock);
                }
                // Badge = the next action's price: ★ to reach the tier, then ✦ to
                // unlock, then 🪙 to buy. Owned animals need nothing.
                if (state !== 'owned') {
                    const cost = document.createElement('span');
                    cost.className = 'az-node-cost';
                    if (state === 'buyable' || state === 'buypoor') {
                        cost.classList.add('coin');
                        cost.innerHTML = coinImg() + a.cost_coins;
                    } else if (state === 'tierlocked') {
                        cost.classList.add('star');
                        cost.innerHTML = `★${a.tier_threshold}`;
                    } else {
                        cost.innerHTML = `✦${a.skill_cost}`;
                    }
                    node.appendChild(cost);
                }

                const label = document.createElement('div');
                label.className = 'az-node-label';
                label.textContent = known ? a.name : '???';
                node.appendChild(label);

                node.addEventListener('click', () => {
                    if (state === 'owned') {
                        showToast(`${a.name} is in your zoo — place it from the Zoo tab.`, false);
                    } else if (state === 'buyable') {
                        pycmd(`buyAnimal:${a.id}`);
                    } else if (state === 'buypoor') {
                        showToast(`Need ${a.cost_coins} coins to buy ${a.name}.`, true);
                    } else if (state === 'ready') {
                        pycmd(`unlockAnimal:${a.id}`);
                    } else if (state === 'avail') {
                        showToast(`Need ${a.skill_cost} skill points to unlock ${a.name}.`, true);
                    } else {
                        showToast(`Earn ${a.tier_threshold}★ in ${a.biome} to reach ${a.tier_name} animals.`, true);
                    }
                });

                tree.appendChild(node);
            }));
        });
    }

    // ---------- Daily Quests ----------
    function renderQuests() {
        const container = document.getElementById('az-quests');
        container.innerHTML = '';
        const quests = DATA.quests || [];

        if (quests.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'az-quests-empty';
            empty.textContent = 'No quests yet -- answer a few cards to roll today\'s quests.';
            container.appendChild(empty);
            return;
        }

        quests.forEach((q) => {
            const unopened = q.completed && !q.claimed;
            const card = document.createElement('div');
            card.className = 'az-quest-card' + (q.completed ? ' completed' : '')
                + (unopened ? ' unopened' : '');

            const labelRow = document.createElement('div');
            labelRow.className = 'az-quest-label';
            const labelText = document.createElement('span');
            labelText.textContent = q.label;
            labelRow.appendChild(labelText);
            if (q.completed) {
                const check = document.createElement('span');
                check.className = 'az-quest-check';
                check.textContent = '✓ Done';
                labelRow.appendChild(check);
            }
            card.appendChild(labelRow);

            const bar = document.createElement('div');
            bar.className = 'az-quest-bar';
            const fill = document.createElement('div');
            fill.className = 'az-quest-bar-fill';
            const pct = q.target > 0 ? Math.min(100, (q.progress / q.target) * 100) : 100;
            fill.style.width = pct + '%';
            bar.appendChild(fill);
            card.appendChild(bar);

            const meta = document.createElement('div');
            meta.className = 'az-quest-meta';
            const progressText = document.createElement('span');
            progressText.textContent = `${q.progress} / ${q.target}`;
            meta.appendChild(progressText);

            // Reward side: a mystery loot box until the quest is done, an "Open"
            // button once completed, then the revealed prize after opening.
            if (q.claimed && q.claimed_reward) {
                meta.appendChild(rewardChip(q.claimed_reward));
            } else if (unopened) {
                const btn = document.createElement('button');
                btn.className = 'az-loot-open';
                btn.innerHTML = '\u{1F381} Open Loot Box';
                btn.addEventListener('click', () => {
                    btn.disabled = true;
                    pycmd(`claimQuest:${q.id}`);
                });
                meta.appendChild(btn);
            } else {
                const teaser = document.createElement('span');
                teaser.className = 'az-loot-teaser';
                teaser.innerHTML = '\u{1F381} Loot box';
                meta.appendChild(teaser);
            }

            card.appendChild(meta);
            container.appendChild(card);
        });
    }

    // A small chip showing a resolved reward, rarity-bordered.
    function rewardChip(reward) {
        const chip = document.createElement('span');
        chip.className = 'az-reward-chip';
        const color = (DATA.rarityColors || {})[reward.rarity] || '#9aa0a6';
        chip.style.setProperty('--rarity', color);
        chip.innerHTML = rewardText(reward);
        return chip;
    }

    function rewardText(reward) {
        if (reward.kind === 'coins') return `${coinImg()} ${reward.amount}`;
        if (reward.kind === 'skill') return `✦ ${reward.label}`;
        if (reward.kind === 'animal') return `\u{1F43E} ${reward.label}`;
        return reward.label || '';
    }

    function renderAll() {
        renderHeader();
        renderMap();
        renderTree();
        renderQuests();
        renderColorPickers();
        renderReviewerToggles();
        renderReviewerStyle();
    }

    // ---------- Bridge update handler ----------
    window.ankiZooApplyUpdate = function (result) {
        if (result.payload) {
            DATA = result.payload;
            window.ANKIZOO_DATA = DATA;
            rebuildCatalogIndex();
            renderAll();
        }
        // A freshly claimed quest returns its rolled reward; play the reveal.
        if (result.loot && result.loot.reward) {
            openCaseModal(result.loot.reward);
        } else if (result.message) {
            showToast(result.message, !result.success);
        }
    };

    function showFatalError(detail) {
        const main = document.querySelector('.az-main');
        if (main) {
            main.innerHTML = `<p style="padding:20px;color:#e08a8a;">ankiZoo failed to load: ${detail}</p>`;
        }
        console.error('ankiZoo:', detail);
    }

    function boot() {
        DATA = window.ANKIZOO_DATA;
        if (!DATA) {
            showFatalError('window.ANKIZOO_DATA was not set.');
            return;
        }
        rebuildCatalogIndex();

        document.getElementById('az-modal-overlay').addEventListener('click', (e) => {
            if (e.target.id === 'az-modal-overlay') closeModal();
        });

        function activateTab(tabName) {
            const btn = document.querySelector(`.az-tab-btn[data-tab="${tabName}"]`);
            const panel = document.getElementById('az-tab-' + tabName);
            if (!btn || !panel) return;
            document.querySelectorAll('.az-tab-btn').forEach((b) => b.classList.remove('active'));
            document.querySelectorAll('.az-tab-panel').forEach((p) => p.classList.remove('active'));
            btn.classList.add('active');
            panel.classList.add('active');
            // The stage has no width until the Zoo tab is visible, so fit the map
            // the first time it's shown.
            if (tabName === 'zoo' && !mapFitted) requestAnimationFrame(fitMap);
        }

        document.querySelectorAll('.az-tab-btn').forEach((btn) => {
            btn.addEventListener('click', () => activateTab(btn.dataset.tab));
        });
        if (DATA.initialTab) activateTab(DATA.initialTab);

        document.getElementById('az-reset-btn').addEventListener('click', openResetConfirmModal);
        setupColorPickers();
        setupTooltip();
        setupReviewerToggles();
        setupReviewerStyle();
        setupMapControls();
        window.addEventListener('resize', () => { if (mapFitted) { clampMap(); applyMapTransform(); } });

        setInterval(() => {
            blinkOn = !blinkOn;
            document.querySelectorAll('.az-sprite, .az-node-sprite').forEach((img) => {
                img.src = blinkOn ? img.dataset.blinkUri : img.dataset.idleUri;
            });
        }, 900);

        renderAll();
    }

    try {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', boot);
        } else {
            boot();
        }
    } catch (e) {
        showFatalError(e.message || String(e));
    }
})();
