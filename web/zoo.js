(function () {
    let DATA = null;
    let catalogById = {};
    let blinkOn = false;
    let prevCoins = null;

    function rebuildCatalogIndex() {
        catalogById = {};
        DATA.catalog.forEach((a) => { catalogById[a.id] = a; });
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

    function openPlaceAnimalModal(x, y) {
        const placedIds = new Set(Object.values(DATA.placedAnimals));
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
                    pycmd(`placeAnimal:${x},${y}|${animalId}`);
                    closeModal();
                });
            });
        }
        modal.querySelector('.az-modal-close').addEventListener('click', closeModal);
        document.getElementById('az-modal-overlay').classList.add('show');
    }

    function openManageTileModal(x, y, animalId) {
        const a = catalogById[animalId];
        const modal = document.getElementById('az-modal');
        modal.innerHTML = `<h3>${a.name}</h3>
            <img src="${a.sprite_idle_uri}" style="width:64px;height:64px;image-rendering:pixelated;display:block;margin:0 auto 10px;">
            <button class="az-modal-remove">Remove from tile</button>
            <button class="az-modal-close">Close</button>`;
        modal.querySelector('.az-modal-remove').addEventListener('click', () => {
            pycmd(`removeAnimal:${x},${y}`);
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
            icon.textContent = '\u{1FA99}';
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
        if (reward.kind === 'coins') return `\u{1FA99} ${reward.amount} coins`;
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
        coinsEl.textContent = DATA.coins;
        prevCoins = DATA.coins;
    }

    // Renders a placed entity onto an owned tile: an inset habitat patch
    // carrying its own biome terrain, an optional fence, and the bobbing sprite.
    // Buildings (once their art lands) reuse this with their own sprite/terrain
    // and typically `fence: false` -- see the placement branch in renderGrid.
    function renderPlaceable(tile, opts) {
        const terrain = opts.terrain;
        const terrainImg = terrain && DATA.terrainImages[terrain.biome];
        if (terrainImg) {
            const habitat = document.createElement('div');
            habitat.className = 'az-habitat';
            habitat.style.backgroundImage = `url(${terrainImg.uri})`;
            habitat.style.backgroundPosition = `-${terrain.ox}px -${terrain.oy}px`;
            habitat.style.backgroundSize = `${terrainImg.w}px ${terrainImg.h}px`;
            tile.appendChild(habitat);
        }
        if (opts.fence) {
            const fence = document.createElement('img');
            fence.className = 'az-fence';
            fence.src = DATA.fenceUri;
            tile.appendChild(fence);
        }
        const img = document.createElement('img');
        img.dataset.idleUri = opts.idleUri;
        img.dataset.blinkUri = opts.blinkUri || opts.idleUri;
        img.src = img.dataset.idleUri;
        img.className = 'az-sprite';
        if (opts.onClick) img.addEventListener('click', opts.onClick);
        tile.appendChild(img);
    }

    // ---------- Grid ----------
    function renderGrid() {
        const grid = document.getElementById('az-grid');
        grid.innerHTML = '';
        const ownedSet = new Set(DATA.ownedTiles.map((t) => t[0] + ',' + t[1]));

        for (let y = 0; y < DATA.gridSize; y++) {
            for (let x = 0; x < DATA.gridSize; x++) {
                const key = x + ',' + y;
                const tile = document.createElement('div');
                tile.className = 'az-tile';
                if ((x + y) % 2 === 0) tile.classList.add('az-tile-alt');
                tile.dataset.x = x;
                tile.dataset.y = y;

                if (ownedSet.has(key)) {
                    const animalId = DATA.placedAnimals[key];
                    if (animalId && catalogById[animalId]) {
                        tile.classList.add('owned');
                        renderPlaceable(tile, {
                            terrain: DATA.tileTerrain[key],
                            fence: true,
                            idleUri: catalogById[animalId].sprite_idle_uri,
                            blinkUri: catalogById[animalId].sprite_blink_uri,
                            onClick: () => openManageTileModal(x, y, animalId),
                        });
                    } else {
                        tile.classList.add('owned', 'empty-owned');
                        tile.addEventListener('click', () => openPlaceAnimalModal(x, y));
                    }
                } else if (isAdjacentToOwned(x, y, ownedSet)) {
                    tile.classList.add('buyable');
                    tile.title = `Buy tile: ${DATA.nextTileCost} coins`;
                    const costLabel = document.createElement('div');
                    costLabel.className = 'az-tile-cost';
                    costLabel.textContent = DATA.nextTileCost;
                    tile.appendChild(costLabel);
                    tile.addEventListener('click', () => pycmd(`buyTile:${x},${y}`));
                } else {
                    tile.classList.add('locked');
                }

                grid.appendChild(tile);
            }
        }
    }

    function isAdjacentToOwned(x, y, ownedSet) {
        return ownedSet.has((x + 1) + ',' + y) || ownedSet.has((x - 1) + ',' + y) ||
               ownedSet.has(x + ',' + (y + 1)) || ownedSet.has(x + ',' + (y - 1));
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
                    t = { tier: a.conservation, name: a.tier_name, threshold: a.tier_threshold, rank: a.tier_rank, animals: [] };
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
        const accessible = (stars[a.biome] || 0) >= a.tier_threshold;
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
                const passed = (stars[b.biome] || 0) >= t.threshold;
                const gate = document.createElement('div');
                gate.className = 'az-gate' + (passed ? ' open' : ' closed');
                gate.style.left = b.x + 'px';
                gate.style.top = L.slotY(t.gateSlot) + 'px';
                gate.style.setProperty('--biome-color', b.color);
                gate.innerHTML = `★${t.threshold} <span>${t.tier}</span>`;
                gate.title = passed
                    ? `${t.name} unlocked`
                    : `Earn ${t.threshold}★ in ${b.biome} to reach ${t.name}`;
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
                node.title = `${a.name} — ${a.tier_name} (worth ★${a.star_value})\n`
                    + `Unlock: ✦${a.skill_cost} skill pts   Buy: \u{1FA99}${a.cost_coins} coins`;

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
                        cost.innerHTML = `\u{1FA99}${a.cost_coins}`;
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
        chip.textContent = rewardText(reward);
        return chip;
    }

    function rewardText(reward) {
        if (reward.kind === 'coins') return `\u{1FA99} ${reward.amount}`;
        if (reward.kind === 'skill') return `✦ ${reward.label}`;
        if (reward.kind === 'animal') return `\u{1F43E} ${reward.label}`;
        return reward.label || '';
    }

    function renderAll() {
        renderHeader();
        renderGrid();
        renderTree();
        renderQuests();
        renderColorPickers();
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
        }

        document.querySelectorAll('.az-tab-btn').forEach((btn) => {
            btn.addEventListener('click', () => activateTab(btn.dataset.tab));
        });
        if (DATA.initialTab) activateTab(DATA.initialTab);

        document.getElementById('az-reset-btn').addEventListener('click', openResetConfirmModal);
        setupColorPickers();

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
