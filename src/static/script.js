document.addEventListener('DOMContentLoaded', async () => {
    const inputs = {
        year: document.getElementById('year'),
        region_selector: document.getElementById('region_selector'),
        grp: document.getElementById('grp'),
        income: document.getElementById('income'),
        unemployment: document.getElementById('unemployment'),
        subsidies: document.getElementById('subsidies')
    };

    const valueDisplays = {
        year: document.getElementById('year_val'),
        grp: document.getElementById('grp_val'),
        income: document.getElementById('income_val'),
        unemployment: document.getElementById('unemp_val'),
        subsidies: document.getElementById('subs_val')
    };

    const resultBox = document.getElementById('prediction_result');
    const trendBox = document.getElementById('trend');
    const adviceBox = document.getElementById('advice_text');

    let regionsDataSet = []; // для хранения извлеченных данных

    // 1. Инициализация (Загрузка 85 регионов)
    try {
        const r = await fetch('/get_regions');
        const d = await r.json();
        if (d.status === 'success') {
            const selectEl = document.getElementById('region_selector');
            selectEl.innerHTML = '<option value="">Выберите регион...</option>';
            
            regionsDataSet = d.regions;
            
            d.regions.forEach(reg => {
                const opt = document.createElement('option');
                opt.value = reg.Region_Name;
                opt.innerText = reg.Region_Name;
                selectEl.appendChild(opt);
            });
            
            // Запуск библиотеки поиска TomSelect
            new TomSelect("#region_selector",{
                create: false,
                sortField: { field: "text", direction: "asc" }
            });
        }
    } catch(e) { console.error("Ошибка загрузки регионов"); }

    const updateDisplays = () => {
        valueDisplays.year.innerText = `${inputs.year.value} г.`;
        valueDisplays.grp.innerText = `${inputs.grp.value} т.р.`;
        valueDisplays.income.innerText = `${inputs.income.value} т.р.`;
        valueDisplays.unemployment.innerText = `${inputs.unemployment.value}%`;
        valueDisplays.subsidies.innerText = `${inputs.subsidies.value} млрд.р.`;
    };

    const lockSliders = (isLocked) => {
        ['grp', 'income', 'unemployment', 'subsidies'].forEach(key => {
            const el = inputs[key];
            if (isLocked) {
                el.setAttribute('disabled', 'true');
                el.style.opacity = '0.5';
                el.style.cursor = 'not-allowed';
            } else {
                el.removeAttribute('disabled');
                el.style.opacity = '1';
                el.style.cursor = 'pointer';
            }
        });
    };

    let currentDetailedText = "";
    let typeWriterInterval;

    const modal = document.getElementById('ai_modal');
    const btnClose = document.getElementById('btn_close_modal');
    const tw = document.getElementById('modal_typewriter');

    document.getElementById('btn_detailed_analysis').addEventListener('click', () => {
        // Открытие модалки
        modal.style.display = 'flex';
        // forced reflow для анимации opacity
        void modal.offsetWidth;
        modal.classList.add('show');
        
        tw.innerHTML = '';
        let i = 0;
        clearInterval(typeWriterInterval);
        
        // Звук печатной машинки
        typeWriterInterval = setInterval(() => {
            if(i < currentDetailedText.length) {
                const char = currentDetailedText.charAt(i);
                tw.innerHTML += char === '\n' ? '<br>' : char;
                tw.scrollTop = tw.scrollHeight;
                i++;
            } else {
                clearInterval(typeWriterInterval);
            }
        }, 10); // быстрый ввод
    });

    btnClose.addEventListener('click', () => {
        modal.classList.remove('show');
        clearInterval(typeWriterInterval);
        setTimeout(() => modal.style.display = 'none', 300); // ждем конец анимации
    });

    const renderData = (val, isHistory, critiqueText, detailedText) => {
        // Плавное затухание текста
        resultBox.style.opacity = 0;
        trendBox.style.opacity = 0;
        adviceBox.style.opacity = 0;

        const intYear = inputs.year.value;

        setTimeout(() => {
            resultBox.innerHTML = `${val > 0 ? '+' : ''}${val.toFixed(2)} <span class="unit">на 10к чел.</span>`;
            resultBox.className = 'prediction-value';
            trendBox.className = 'trend-indicator';

            currentDetailedText = detailedText;
            document.getElementById('btn_detailed_analysis').style.display = 'block';

            if (isHistory) {
                const currentRegion = inputs.region_selector.value;
                resultBox.classList.add('neutral');
                trendBox.innerText = '📖 ФАКТ РОССТАТА';
                trendBox.style.background = 'rgba(56, 189, 248, 0.2)';
                trendBox.style.color = '#38bdf8';
                adviceBox.innerHTML = critiqueText;
            } else {
                if (val > 6) {
                    resultBox.classList.add('positive');
                    trendBox.innerText = '🚀 ПРОГНОЗ: Значительный приток';
                    trendBox.style.background = 'rgba(74, 222, 128, 0.2)';
                    trendBox.style.color = '#4ade80';
                    adviceBox.innerHTML = 'Социальная инфраструктура может перегреться. <b>Совет:</b> направляйте новые кадры в строительство жилья.';
                } else if (val > 1) {
                    resultBox.classList.add('positive');
                    trendBox.innerText = '📊 ПРОГНОЗ: Слабый приток';
                    trendBox.style.background = 'rgba(74, 222, 128, 0.2)';
                    trendBox.style.color = '#4ade80';
                    adviceBox.innerHTML = 'Позитивная динамика. <b>Совет:</b> постепенно стимулируйте рабочие места для поддержания тренда.';
                } else if (val < -6) {
                    resultBox.classList.add('negative');
                    trendBox.innerText = '⚠️ ПРОГНОЗ: Серьезный отток';
                    trendBox.style.background = 'rgba(248, 113, 113, 0.2)';
                    trendBox.style.color = '#f87171';
                    adviceBox.innerHTML = 'Катастрофический риск! <b>Совет:</b> необходимо увеличить дотации и снизить безработицу госпроектами.';
                } else if (val < -1) {
                    resultBox.classList.add('negative');
                    trendBox.innerText = '📉 ПРОГНОЗ: Незначительный отток';
                    trendBox.style.background = 'rgba(248, 113, 113, 0.2)';
                    trendBox.style.color = '#f87171';
                    adviceBox.innerHTML = 'Молодежь уезжает. <b>Совет:</b> проработайте программы льготной ипотеки.';
                } else {
                    resultBox.classList.add('neutral');
                    trendBox.innerText = '⚖️ ПРОГНОЗ: Без изменений';
                    trendBox.style.background = 'rgba(255, 255, 255, 0.1)';
                    trendBox.style.color = '#f8fafc';
                    adviceBox.innerHTML = 'Баланс стабилен. <b>Совет:</b> поддерживайте экономические показатели.';
                }
            }

            // Плавное проявление измененного текста
            resultBox.style.opacity = 1;
            trendBox.style.opacity = 1;
            adviceBox.style.opacity = 1;
        }, 150);
    }

    let timeoutId;
    const fetchBrain = async () => {
        const year = parseInt(inputs.year.value);
        const regionName = inputs.region_selector.value;
        
        if (!regionName || regionName === "") {
            document.getElementById('advice_text').innerHTML = "Пожалуйста, выберите регион для начала работы.";
            document.getElementById('btn_detailed_analysis').style.display = 'none';
            return;
        }
        
        // Получить тип региона из базы (или default)
        const foundReg = regionsDataSet.find(r => r.Region_Name === regionName);
        const regionType = foundReg ? foundReg.Region_Type : 'average';

        try {
            if (year <= 2025) {
                // ИСТОРИЯ
                lockSliders(true);
                const r = await fetch('/get_history', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ region: regionName, year: year })
                });
                const data = await r.json();
                if (data.status === 'success') {
                    // Дергаем ползунки программно к факту
                    inputs.grp.value = data.grp;
                    inputs.income.value = data.income;
                    inputs.unemployment.value = data.unemployment;
                    inputs.subsidies.value = data.subsidies;
                    
                    updateDisplays();
                    renderData(data.migration_rate, true, data.critique, data.detailed);
                }
            } else {
                // ПРОГНОЗ
                lockSliders(false);
                const r = await fetch('/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        year: year,
                        region_type: regionType,
                        grp: inputs.grp.value,
                        income: inputs.income.value,
                        unemployment: inputs.unemployment.value,
                        subsidies: inputs.subsidies.value
                    })
                });
                const data = await r.json();
                if (data.status === 'success') {
                    renderData(data.migration_rate, false, null, data.detailed);
                }
            }
        } catch(e) { console.error('Error:', e); }
    };

    const handleChange = () => {
        updateDisplays();
        clearTimeout(timeoutId);
        timeoutId = setTimeout(fetchBrain, 30);
    };

    Object.values(inputs).forEach(input => {
        input.addEventListener('input', handleChange);
    });
    
    // Логика Чата
    const chatWidget = document.getElementById('chat_widget');
    const btnToggleChat = document.getElementById('btn_toggle_chat');
    const btnSendChat = document.getElementById('btn_send_chat');
    const chatInput = document.getElementById('chat_input');
    const chatMessages = document.getElementById('chat_messages');

    // Глобальная память чата
    window.chatHistory = [];

    // Сворачивание чата (можно кликать по всей шапке)
    document.querySelector('.chat-header').addEventListener('click', () => {
        chatWidget.classList.toggle('collapsed');
    });

    const addBubble = (text, isUser) => {
        const div = document.createElement('div');
        div.className = `chat-bubble ${isUser ? 'user-bubble' : 'ai-bubble'}`;
        if (isUser) {
            div.innerHTML = text.replace(/\n/g, '<br>');
        }
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return div; 
    };

    const typeWriterBubble = (text, div) => {
        div.innerHTML = '';
        let i = 0;
        const speed = 15; // Скорость появления букв
        const interval = setInterval(() => {
            if(i < text.length) {
                const char = text.charAt(i);
                if (char === '<') {
                    // Проглатываем HTML теги (например <b>...</b>) целиком за 1 тик
                    const closing = text.indexOf('>', i);
                    if (closing !== -1) {
                        div.innerHTML += text.substring(i, closing + 1);
                        i = closing + 1;
                    } else {
                        div.innerHTML += '&lt;';
                        i++;
                    }
                } else {
                    div.innerHTML += char === '\n' ? '<br>' : char;
                    i++;
                }
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } else {
                clearInterval(interval);
            }
        }, speed);
    };

    const sendMessage = async () => {
        const text = chatInput.value.trim();
        if(!text) return;

        addBubble(text, true);
        chatInput.value = '';
        
        // Запоминаем вопрос пользователя
        window.chatHistory.push({role: "user", content: text});
        // Если история слишком длинная, удаляем старые сообщения
        if (window.chatHistory.length > 20) {
            window.chatHistory = window.chatHistory.slice(window.chatHistory.length - 20);
        }
        
        // Показываем плацехолдер ответа
        const typingBubble = addBubble('Печатает...', false);

        try {
            const r = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: text,
                    history: window.chatHistory,
                    context: {
                        region: inputs.region_selector.value,
                        unemployment: inputs.unemployment.value,
                        grp: inputs.grp.value,
                        subsidies: inputs.subsidies.value
                    }
                })
            });
            const d = await r.json();
            if (d.status === 'success') {
                typingBubble.remove();
                
                // Автовыбор региона, если ИИ его распознал
                if (d.set_region) {
                    const ts = inputs.region_selector.tomselect;
                    if (ts) {
                        ts.setValue(d.set_region); // Это триггернет 'change' событие и обновит дашборд
                    } else {
                        inputs.region_selector.value = d.set_region;
                        handleChange();
                    }
                }

                const aiDiv = addBubble('', false);
                typeWriterBubble(d.answer, aiDiv);
                
                // Добавляем ответ ИИ в историю
                window.chatHistory.push({role: "assistant", content: d.answer});
            }
        } catch(e) {
            typingBubble.innerText = 'Ошибка связи с сервером.';
        }
    };

    btnSendChat.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if(e.key === 'Enter') sendMessage();
    });

    // TomSelect вызывает 'change' на исходном select
    inputs.region_selector.addEventListener('change', handleChange);

    // Стартовый пинг
    setTimeout(handleChange, 200); // ждем загрузки get_regions
});
