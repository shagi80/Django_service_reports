// скрипт для страницы записи о ремонте

// проверка поодержки формата "date"
var i = document.createElement("input");
i.setAttribute("type", "date");
if (i.type == "text") {
    text = 'Ваш браузер не поддерживает формат "date" !\nСообщите об этои администратору сайта !'
    alert(text)
}

// пказ спинера в модальном окне
$('#modalButtons').click(function(){
    $(this).hide();
    $('#modalButtonsSpin').show();
})

// скрытие/показ виджета ввода e-mail клиента
function show_client_email(){
    let check = $('#id_client_type').val();
    if (check == 'organization') {
        $('#client_email_div').prop("hidden", false);
    } else {
        $('#client_email_div').prop("hidden", true);
        $('#id_client_email').val("");
    };
};

//выбор виджете выбора модели - Select или Char
function HideModelWgt(){
    if($("#id_model").find('option').length>1){
      $("#id_model").prop("hidden", false)
      var edit_model = $("#id_model_description").prop("disabled")
      $("#id_model").prop("disabled", edit_model)
      //$("#id_model").prop("disabled", false)
      $("#id_model_description").prop("hidden", true)
      $("#id_model_description").val("")
      }
      else {
      $("#id_model").prop("hidden", true)
      $("#id_model").prop("disabled", true)
      $("#id_model_description").prop("hidden", false)
      }
}

//управление доступностью виджета даты покупки в зависимости от типа ремонта
function SetNuyDateWgt(){
    var val = $("#id_work_type").val();
    if(val == "pretrading"){
            $("#id_buy_date").prop("disabled", true)
            $("#id_buy_date").val(null)
        }else{
            $("#id_buy_date").prop("disabled", false);
        }
}

//подсчет общей суммы
function CalkTotalCost(){
    var work = $("#id_work_cost").val();
    var move = $("#id_move_cost").val();
    var parts = $("#parts_cost").val();
    var sum = Number(work) + Number(move) + Number(parts);
    $("#id_total_cost").val(Number(sum));
    $("#total_cost").val(Number(sum));
}

//подсчет общей стоимости деталей
function CalkPartsTotalCost(){
    var sum = 0;
    var form_count = $("#id_parts_formset-TOTAL_FORMS").val();
    for (let i = 0; i < form_count; i++) {
        if($("#id_parts_formset-"+String(i)+"-ORDERED").prop("checked") != true){
            sum = sum + Number($("#id_parts_formset-"+String(i)+"-price").val()) * 
                Number($("#id_parts_formset-"+String(i)+"-count").val());
            };
    };
    $("#id_parts_cost").val(Number(sum));
    $("#parts_cost").val(Number(sum));
    CalkTotalCost();
}

//добавление событий к полям формсета по аттрибуту "data-counter"
document.addEventListener('change', function(event) {
    if (event.target.dataset.counter != undefined) {
        CalkPartsTotalCost();
    }
});

//действия после рендеринга страницы
$(document).ready(function() {
    var codeId = $("#id_code").val();
    var productId = $("#id_product").val();
    var url1 = $("#recordForm").attr("data-codes-url");
    if((productId)&&(productId>0)){
        $.ajax({
            url: url1,
            data: {'product': productId, 'code': codeId},
            success: function (data) {$("#id_code").html(data);}
        });
    };
    HideModelWgt();
    CalkPartsTotalCost();
    SetNuyDateWgt();
    show_client_email();
    $('#warningModal').modal('show');
    // подключение события к полям "Заказать деталь" b "Удалить делать при записи"  
    $(".part_flag").change(function () {CalkPartsTotalCost();});
    // подключение событий к полям ввода сумм
    $("#id_work_cost").change(function () {CalkTotalCost();});
    $("#id_move_cost").change(function () {CalkTotalCost();});
    // подключение события к полю выбора типа ремонта
    $("#id_work_type").change(function () {SetNuyDateWgt();});
    // подключение событий к полю ввода типа клиента
    $('#id_client_type').change(show_client_email);
});

//заполнение Select-ов выбора модели и кода в зависимости от типа продукции
$("#id_product").change(function () {
    var url1 = $("#recordForm").attr("data-codes-url");
    var url2 = $("#recordForm").attr("data-models-url");
    var productId = $(this).val();

    $.ajax({
      url: url1,
      data: {'product': productId},
      success: function (data) {$("#id_code").html(data);}
    });

    $.ajax({
      url: url2,
      data: {'product': productId},
      success: function (data) {$("#id_model").html(data); HideModelWgt();}
    });

    $("#id_work_cost").val(Number('0'));

});

//клонирование последней формы формсета
$("#AddPart").click(function (e){
    e.preventDefault()
    var form_count = $("#id_parts_formset-TOTAL_FORMS").val();
    let formRegex = RegExp("parts_formset-(\\d){1}-","g")

    $("#parts_container").append($("div.parts_form:last").html().replace(formRegex, "parts_formset-"+String(form_count)+"-"));
    $("#id_parts_formset-TOTAL_FORMS").val(parseInt(form_count) + 1);
    var res_count = $("#id_parts_formset-TOTAL_FORMS").val();

});

//запретить отпраку формы нажатием Enter
$(document).ready(function() {
    $(window).keydown(function(event){
        if(event.keyCode == 13) {
            event.preventDefault();
            return false;
        }
    });
});

//установка цены в зависимости от выбранного кода
$("#id_code").change(function () {
    var url1 = $("#recordForm").attr("data-work-price-url");
    var codeId = $(this).val();
    var reportId = $("#id_report").val();

    $.ajax({
      url: url1,
      data: {'code': codeId, 'report':reportId},
      success: function (data) {$("#id_work_cost").val(Number(data));CalkTotalCost();}
    });

  });

// блоктровка кнопок отправки формы
$('#recordForm').submit(function(){
    $('#buttons').hide();
    $('#buttons_disabled').show();
});

