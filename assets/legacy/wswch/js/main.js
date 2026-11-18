$(document).ready(function () {
  $('[data-toggle="popover"]').popover({delay: {'show': 500, 'hide': 100}})
  var nr = 0
  var newNr = 0
  var title = 0
  var author = 0
  var imgName = 0
  var pages = 0
  var date = 0
  var availability = 0

  $('#imgModal').on('shown.bs.modal', function (e) {
    if (nr !== newNr) {
      $('#imgModal #newsp-title').html(title)
      $('#imgModal #newsp-author').html(author)
      $('#imgModal #newsp-pages').html(pages)
      $('#imgModal #newsp-date').html(date)
      $('#imgModal #newsp-number').html(newNr)
      $('#imgModal #newsp-availability').html(availability)

      var container = $('.modal-body')
      container.find('#left-img').html('<a href=\'images/' + imgName + '_a.jpg\' target=\'_blank\'><img src=\'images/' + imgName + '_a.jpg\' alt=\'\' /></a>')
      container.find('#right-img').html('<a href=\'images/' + imgName + '_b.jpg\' target=\'_blank\'><img src=\'images/' + imgName + '_b.jpg\' alt=\'\' /></a>')
      nr = newNr
    }
    ga('send', 'event', 'modalInfo', 'show', title)
  })

  $('button.img-label').click(function () {
    newNr = $(this).data('nr')
    title = $(this).data('title')
    author = $(this).data('author')
    imgName = $(this).data('img')
    pages = $(this).data('pages')
    date = $(this).data('date')
    availability = $(this).data('availability')
  })

  $('.nav-item.nav-link').click(function () {
    var tabVer = $(this).attr('href')
    ga('send', 'event', 'openTab', 'Click', tabVer)
  })

  $('#informator_wydawniczy').click(function () {
    ga('send', 'event', 'openInfo', 'Click', true)
  })

  $('#nav-gazetki table tbody tr').mouseover(function () {
    $(this).find('[data-toggle="popover"]').popover('show')
  }).mouseout(function () {
    $(this).find('[data-toggle="popover"]').popover('hide')
  })



  $('.btn-order').click(function () {
    $('html, body').animate({
      scrollTop: $('#order-details').offset().top - 20
    }, 600, function () {
      $('#order-details').addClass('active')
      setTimeout(function(){
        $('#order-details').removeClass('active');
      }, 3000);
    })
  })

})