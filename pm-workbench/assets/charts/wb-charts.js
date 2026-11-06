/* Chart helpers for internal and teammate HTML.
   Load echarts.min.js and a generated theme script before this file. */
(function (global) {
    "use strict";

    var live = [];

    function nodeOf(container) {
        if (typeof container === "string") {
            var found = document.getElementById(container);
            if (!found) {
                throw new Error("Chart container not found: " + container);
            }
            return found;
        }
        if (container && container.nodeType === 1) {
            return container;
        }
        throw new Error("Chart container must be an element or an id.");
    }

    function packFor(themeName) {
        var packs = global.WB_THEMES || {};
        if (!packs[themeName]) {
            throw new Error("Chart theme is not loaded: " + themeName);
        }
        return packs[themeName];
    }

    function seriesColor(pack, series, index) {
        var roles = pack.wb && pack.wb.roles;
        if (series && series.role && roles && roles[series.role]) {
            return roles[series.role];
        }
        var colors = pack.color || [];
        if (!colors.length) {
            return "#333333";
        }
        return colors[index % colors.length];
    }

    function ensureHeight(node) {
        if (node.clientHeight < 40) {
            node.style.height = "240px";
        }
    }

    function captionText(caption) {
        var source = caption || {};
        var population = source.population || "";
        var windowLabel = source.window || "";
        var denominator = source.denominator || "";
        return (
            "Population: " + population +
            ". Window: " + windowLabel +
            ". Denominator: " + denominator +
            "."
        );
    }

    function renderCaption(node, caption) {
        var next = node.nextElementSibling;
        if (next && next.classList && next.classList.contains("wb-chart-caption")) {
            next.remove();
        }
        var el = document.createElement("p");
        el.className = "wb-chart-caption";
        el.textContent = captionText(caption);
        node.insertAdjacentElement("afterend", el);
        return el;
    }

    function mount(container, themeName) {
        if (!global.echarts) {
            throw new Error("ECharts is not loaded.");
        }
        var node = nodeOf(container);
        ensureHeight(node);
        var existing = global.echarts.getInstanceByDom(node);
        if (existing) {
            existing.dispose();
        }
        var chart = global.echarts.init(node, themeName);
        live = live.filter(function (item) {
            return !item.isDisposed();
        });
        live.push(chart);
        return { node: node, chart: chart, pack: packFor(themeName) };
    }

    function baseGrid() {
        return { left: 48, right: 24, top: 36, bottom: 28, containLabel: true };
    }

    function barCompare(container, data, themeName, caption) {
        var view = mount(container, themeName);
        var source = data || {};
        var series = (source.series || []).map(function (item, index) {
            return {
                name: item.name,
                type: "bar",
                data: item.values || [],
                itemStyle: { color: seriesColor(view.pack, item, index) }
            };
        });
        view.chart.setOption({
            legend: { show: series.length > 1 },
            grid: baseGrid(),
            xAxis: { type: "category", data: source.categories || [] },
            yAxis: { type: "value", min: 0 },
            series: series
        });
        renderCaption(view.node, caption);
        return view.chart;
    }

    function lineSeries(container, data, themeName, caption) {
        var view = mount(container, themeName);
        var source = data || {};
        var roles = (view.pack.wb && view.pack.wb.roles) || {};
        var series = (source.series || []).map(function (item, index) {
            var row = {
                name: item.name,
                type: "line",
                data: item.values || [],
                showSymbol: true,
                lineStyle: { color: seriesColor(view.pack, item, index), width: 2 },
                itemStyle: { color: seriesColor(view.pack, item, index) }
            };
            if (index === 0 && source.bands && source.bands.length) {
                row.markArea = {
                    silent: true,
                    itemStyle: { color: roles.annotation || "#CCCCCC", opacity: 0.18 },
                    data: source.bands.map(function (band) {
                        return [
                            { name: band.label || "", xAxis: band.from },
                            { xAxis: band.to }
                        ];
                    })
                };
            }
            return row;
        });
        view.chart.setOption({
            legend: { show: series.length > 1 },
            grid: baseGrid(),
            xAxis: { type: "category", data: source.x || [] },
            yAxis: { type: "value", min: 0 },
            series: series
        });
        renderCaption(view.node, caption);
        return view.chart;
    }

    function funnel(container, data, themeName, caption) {
        var view = mount(container, themeName);
        var stages = ((data || {}).stages || []).map(function (stage, index) {
            return {
                name: stage.name,
                value: stage.value,
                itemStyle: { color: seriesColor(view.pack, stage, index) }
            };
        });
        view.chart.setOption({
            series: [{
                type: "funnel",
                left: "10%",
                right: "10%",
                top: 16,
                bottom: 16,
                sort: "none",
                minSize: "8%",
                label: { color: view.pack.wb.text, fontFamily: view.pack.wb.font },
                data: stages
            }]
        });
        renderCaption(view.node, caption);
        return view.chart;
    }

    function heatmap(container, data, themeName, caption) {
        var view = mount(container, themeName);
        var source = data || {};
        var xLabels = source.x || [];
        var yLabels = source.y || [];
        var cells = [];
        var min = null;
        var max = null;
        (source.values || []).forEach(function (row, yIndex) {
            (row || []).forEach(function (value, xIndex) {
                var number = Number(value);
                cells.push([xIndex, yIndex, number]);
                if (min === null || number < min) min = number;
                if (max === null || number > max) max = number;
            });
        });
        var scale = source.scale === "diverging"
            ? view.pack.wb.diverging
            : view.pack.wb.sequential;
        view.chart.setOption({
            grid: { left: 48, right: 24, top: 16, bottom: 56, containLabel: true },
            xAxis: { type: "category", data: xLabels },
            yAxis: { type: "category", data: yLabels },
            visualMap: {
                min: min === null ? 0 : min,
                max: max === null ? 1 : max,
                orient: "horizontal",
                left: "center",
                bottom: 0,
                inRange: { color: scale },
                textStyle: { color: view.pack.wb.text }
            },
            series: [{ type: "heatmap", data: cells }]
        });
        renderCaption(view.node, caption);
        return view.chart;
    }

    function distribution(container, data, themeName, caption) {
        var view = mount(container, themeName);
        var source = data || {};
        var series = (source.series || []).map(function (item, index) {
            return {
                name: item.name,
                type: "boxplot",
                data: item.values || [],
                itemStyle: {
                    color: seriesColor(view.pack, item, index),
                    borderColor: view.pack.wb.axis
                }
            };
        });
        view.chart.setOption({
            legend: { show: series.length > 1 },
            grid: baseGrid(),
            xAxis: { type: "category", data: source.categories || [] },
            yAxis: { type: "value" },
            series: series
        });
        renderCaption(view.node, caption);
        return view.chart;
    }

    function sankey(container, data, themeName, caption) {
        var view = mount(container, themeName);
        var source = data || {};
        view.chart.setOption({
            series: [{
                type: "sankey",
                data: source.nodes || [],
                links: source.links || [],
                nodeWidth: 14,
                nodeGap: 12,
                left: 16,
                right: 16,
                top: 16,
                bottom: 16,
                label: { color: view.pack.wb.text, fontFamily: view.pack.wb.font },
                lineStyle: { color: "gradient", curveness: 0.4 },
                itemStyle: { borderWidth: 0 }
            }]
        });
        renderCaption(view.node, caption);
        return view.chart;
    }

    global.addEventListener("resize", function () {
        live.forEach(function (chart) {
            if (!chart.isDisposed()) {
                chart.resize();
            }
        });
    });

    global.wbCharts = {
        barCompare: barCompare,
        lineSeries: lineSeries,
        funnel: funnel,
        heatmap: heatmap,
        distribution: distribution,
        sankey: sankey
    };
})(typeof globalThis !== "undefined" ? globalThis : window);
