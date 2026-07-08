(function () {
    let DATA = null;
    let catalogById = {};
    let blinkOn = false;

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
        document.getElementById('az-modal').innerHTML = '';
    }

    function openPlaceAnimalModal(x, y) {
        const placedIds = new Set(Object.values(DATA.placedAnimals));
        const available = DATA.ownedAnimals.filter((id) => !placedIds.has(id));
        const modal = document.getElementById('az-modal');
        if (available.length === 0) {
            modal.innerHTML = '<h3>No animals available</h3><p>Buy an animal from the Collection tab first.</p>' +
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
    function renderHeader() {
        document.getElementById('az-header-rank').textContent = DATA.rank;
        document.getElementById('az-header-level').textContent = 'Lv. ' + DATA.level;
        const pct = DATA.xpToNextLevel > 0 ? Math.min(100, (DATA.xpIntoLevel / DATA.xpToNextLevel) * 100) : 100;
        document.getElementById('az-header-xp-fill').style.width = pct + '%';
        document.getElementById('az-header-xp-label').textContent =
            DATA.xpToNextLevel > 0 ? `${DATA.xpIntoLevel} / ${DATA.xpToNextLevel} XP` : 'Max level';
        document.getElementById('az-header-coins').textContent = DATA.coins;
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
                tile.dataset.x = x;
                tile.dataset.y = y;

                if (ownedSet.has(key)) {
                    const animalId = DATA.placedAnimals[key];
                    if (animalId && catalogById[animalId]) {
                        tile.classList.add('owned');
                        const terrain = DATA.tileTerrain[key];
                        const terrainImg = terrain && DATA.terrainImages[terrain.biome];
                        if (terrainImg) {
                            tile.style.backgroundImage = `url(${terrainImg.uri})`;
                            tile.style.backgroundPosition = `-${terrain.ox}px -${terrain.oy}px`;
                            tile.style.backgroundSize = `${terrainImg.w}px ${terrainImg.h}px`;
                        }
                        const fence = document.createElement('img');
                        fence.className = 'az-fence';
                        fence.src = DATA.fenceUri;
                        tile.appendChild(fence);
                        const img = document.createElement('img');
                        img.dataset.idleUri = catalogById[animalId].sprite_idle_uri;
                        img.dataset.blinkUri = catalogById[animalId].sprite_blink_uri;
                        img.src = img.dataset.idleUri;
                        img.className = 'az-sprite';
                        img.addEventListener('click', () => openManageTileModal(x, y, animalId));
                        tile.appendChild(img);
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

    // ---------- Collection / Dex ----------
    function renderDex() {
        const dex = document.getElementById('az-dex');
        dex.innerHTML = '';
        const ownedSet = new Set(DATA.ownedAnimals);

        DATA.catalog.forEach((a) => {
            const owned = ownedSet.has(a.id);
            const eligible = DATA.level >= a.unlock_level;
            const card = document.createElement('div');
            card.className = 'az-dex-card' + (owned ? '' : ' locked');

            const img = document.createElement('img');
            img.src = a.sprite_idle_uri;
            card.appendChild(img);

            const name = document.createElement('div');
            name.className = 'az-dex-name';
            name.textContent = owned ? a.name : (eligible ? a.name : '???');
            card.appendChild(name);

            const meta = document.createElement('div');
            meta.className = 'az-dex-meta';
            meta.textContent = owned ? a.biome : `Lv. ${a.unlock_level} • ${a.cost_coins} coins`;
            card.appendChild(meta);

            const rarity = document.createElement('span');
            rarity.className = 'az-rarity ' + a.rarity;
            rarity.textContent = a.rarity;
            card.appendChild(rarity);

            if (!owned) {
                const btn = document.createElement('button');
                btn.textContent = 'Buy';
                const affordable = eligible && DATA.coins >= a.cost_coins;
                btn.disabled = !affordable;
                if (!eligible) btn.textContent = `Lv. ${a.unlock_level} needed`;
                else if (DATA.coins < a.cost_coins) btn.textContent = 'Not enough coins';
                btn.addEventListener('click', () => {
                    if (affordable) pycmd(`buyAnimal:${a.id}`);
                });
                card.appendChild(document.createElement('br'));
                card.appendChild(btn);
            }

            dex.appendChild(card);
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
            const card = document.createElement('div');
            card.className = 'az-quest-card' + (q.completed ? ' completed' : '');

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

            const rewardText = document.createElement('span');
            rewardText.className = 'az-quest-reward';
            if (q.reward_type === 'animal' && q.reward_animal_id) {
                const animal = catalogById[q.reward_animal_id];
                rewardText.textContent = animal ? animal.name : 'Mystery animal';
            } else {
                rewardText.textContent = `${q.reward_amount} coins`;
            }
            meta.appendChild(rewardText);

            card.appendChild(meta);
            container.appendChild(card);
        });
    }

    function renderAll() {
        renderHeader();
        renderGrid();
        renderDex();
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
        if (result.message) {
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
            document.querySelectorAll('.az-sprite').forEach((img) => {
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
