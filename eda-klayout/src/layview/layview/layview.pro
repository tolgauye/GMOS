
DESTDIR = $$OUT_PWD/../..
TARGET = klayout_layview

include($$PWD/../../lib.pri)

DEFINES += MAKE_LAYVIEW_LIBRARY

RESOURCES = \

SOURCES = \
  layGridNet.cc \
  layviewForceLink.cc \
  gsiDeclLayAdditional.cc \

HEADERS = \
  layGridNet.h \
  layLayoutView.h \
  layviewForceLink.h \

!equals(HAVE_QT, "0") {

  FORMS = \
    GridNetConfigPage.ui \

  SOURCES += \
    layGridNetConfigPage.cc \
    layLayoutView_qt.cc \
    gsiDeclLayLayoutView_qt.cc \

  HEADERS += \
    layGridNetConfigPage.h \
    layLayoutView_qt.h \

} else {

  SOURCES += \
    layLayoutView_noqt.cc \
    gsiDeclLayLayoutView_noqt.cc \

  HEADERS += \
    layLayoutView_noqt.h \

}

INCLUDEPATH += $$LAYBASIC_INC $$TL_INC $$GSI_INC $$DB_INC $$RDB_INC
DEPENDPATH += $$LAYBASIC_INC $$TL_INC $$GSI_INC $$DB_INC $$RDB_INC
LIBS += -L$$DESTDIR -lklayout_laybasic -lklayout_tl -lklayout_gsi -lklayout_db -lklayout_rdb 

!equals(HAVE_QT, "0") {

  INCLUDEPATH += $$QTBASIC_INC $$LAYUI_INC
  DEPENDPATH += $$QTBASIC_INC $$LAYUI_INC
  LIBS += -lklayout_layui

  equals(HAVE_QTBINDINGS, "1") {
    LIBS += -lklayout_qtbasic -lklayout_QtGui -lklayout_QtCore
    greaterThan(QT_MAJOR_VERSION, 4) {
      LIBS += -lklayout_QtWidgets
    }
  }

}
