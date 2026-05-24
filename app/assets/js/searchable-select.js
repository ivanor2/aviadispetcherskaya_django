// Searchable select functionality
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация поисковых селектов
    const searchableSelects = document.querySelectorAll('.searchable-select');
    
    searchableSelects.forEach(function(select) {
        // Получаем placeholder из data-атрибута
        const placeholder = select.dataset.placeholder || 'Выберите...';
        
        // Оборачиваем select в контейнер
        const wrapper = document.createElement('div');
        wrapper.className = 'searchable-select-wrapper';
        wrapper.style.position = 'relative';
        
        // Создаем поле поиска
        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.className = 'searchable-input';
        searchInput.placeholder = placeholder;
        searchInput.style.cssText = 'width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 6px; font-size: 1rem; box-sizing: border-box;';
        
        // Создаем выпадающий список
        const dropdown = document.createElement('div');
        dropdown.className = 'searchable-dropdown';
        dropdown.style.cssText = 'position: absolute; top: 100%; left: 0; right: 0; background: #fff; border: 1px solid #ddd; border-radius: 6px; max-height: 300px; overflow-y: auto; z-index: 1000; display: none; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
        
        // Копируем опции в dropdown
        Array.from(select.options).forEach(function(option) {
            if (option.value) { // Пропускаем placeholder опцию
                const item = document.createElement('div');
                item.className = 'searchable-option';
                item.textContent = option.textContent;
                item.dataset.value = option.value;
                item.style.cssText = 'padding: 0.75rem; cursor: pointer; transition: background 0.2s;';
                item.onmouseover = function() { this.style.background = '#f0f0f0'; };
                item.onmouseout = function() { this.style.background = ''; };
                item.onclick = function() {
                    select.value = this.dataset.value;
                    searchInput.value = this.textContent;
                    dropdown.style.display = 'none';
                };
                dropdown.appendChild(item);
            }
        });
        
        // Показываем/скрываем dropdown
        searchInput.onfocus = function() {
            dropdown.style.display = 'block';
            filterOptions();
        };
        
        searchInput.onblur = function() {
            setTimeout(function() {
                dropdown.style.display = 'none';
            }, 200);
        };
        
        // Фильтрация опций
        function filterOptions() {
            const query = searchInput.value.toLowerCase();
            Array.from(dropdown.children).forEach(function(item) {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(query) ? 'block' : 'none';
            });
        }
        
        searchInput.oninput = filterOptions;
        
        // Скрываем оригинальный select
        select.style.display = 'none';
        
        // Вставляем элементы
        select.parentNode.insertBefore(wrapper, select);
        wrapper.appendChild(searchInput);
        wrapper.appendChild(dropdown);
        
        // Синхронизация при изменении select извне
        select.onchange = function() {
            const selectedOption = select.options[select.selectedIndex];
            if (selectedOption && selectedOption.value) {
                searchInput.value = selectedOption.textContent;
            } else {
                searchInput.value = '';
            }
        };
        
        // Инициализация значения
        if (select.value) {
            const selectedOption = select.options[select.selectedIndex];
            if (selectedOption && selectedOption.value) {
                searchInput.value = selectedOption.textContent;
            }
        }
    });
});
