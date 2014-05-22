#include <QMessageBox>
#include "mainwindow.h"
#include "ui_mainwindow.h"
extern "C" {
#include "../bip32.h"
#include "../bip39.h"
#include "../ecdsa.h"
}

HDNode root;

MainWindow::MainWindow(QWidget *parent) : QMainWindow(parent), ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    for (int i = 0; i < 100; i++) {
        ui->listAddress->insertRow(i);
        ui->listChange->insertRow(i);

    }
}

MainWindow::~MainWindow()
{
    delete ui;
}

// abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about

void MainWindow::on_buttonLoad_clicked()
{
    ui->listAccount->clear();
    if (!mnemonic_check(ui->editMnemonic->text().toLocal8Bit().data())) {
        QMessageBox::critical(this, "Error", "Text is not a valid BIP39 mnemonic.", QMessageBox::Ok);
        return;
    }
    uint8_t seed[64];
    mnemonic_to_seed(ui->editMnemonic->text().toLocal8Bit().data(), ui->editPassphrase->text().toLocal8Bit().data(), seed, 0);
    hdnode_from_seed(seed, 64, &root);
    for (int i = 1; i <= 10; i++) {
        ui->listAccount->addItem(QString("Account #") + QString::number(i));
    }
}

void MainWindow::on_listAccount_clicked(const QModelIndex &index)
{
    const char addr_version = 0x00, wif_version = 0x80;
    char buf[64];
    HDNode node;
    // external chain
    for (int chain = 0; chain < 2; chain++) {
        QTableWidget *list = chain == 0 ? ui->listAddress : ui->listChange;
        node = root;
        hdnode_private_ckd(&node, 44 | 0x80000000);
        hdnode_private_ckd(&node, index.row() | 0x80000000);
        hdnode_private_ckd(&node, chain); // external / internal
        for (int i = 0; i < 100; i++) {
            HDNode node2 = node;
            hdnode_private_ckd(&node2, i);
            ecdsa_get_address(node2.public_key, addr_version, buf); QString address = QString(buf);
            ecdsa_get_wif(node2.private_key, wif_version, buf); QString wif = QString(buf);
            list->setItem(i, 0, new QTableWidgetItem(address));
            list->setItem(i, 1, new QTableWidgetItem(wif));
            list->setItem(i, 2, new QTableWidgetItem("0.0"));
        }
    }
}
