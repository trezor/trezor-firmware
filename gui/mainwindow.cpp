#include <QMessageBox>
#include "mainwindow.h"
#include "ui_mainwindow.h"
extern "C" {
#include "../bip32.h"
#include "../bip39.h"
#include "../ecdsa.h"
#include "../curves.h"
}

bool root_set = false;
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
    if (!mnemonic_check(ui->editMnemonic->text().toLocal8Bit().data())) {
        QMessageBox::critical(this, "Error", "Text is not a valid BIP39 mnemonic.", QMessageBox::Ok);
        return;
    }
    uint8_t seed[64];
    mnemonic_to_seed(ui->editMnemonic->text().toLocal8Bit().data(), ui->editPassphrase->text().toLocal8Bit().data(), seed, 0);
    hdnode_from_seed(seed, 64, SECP256K1_NAME, &root);
    root_set = true;
    ui->spinAccount->setValue(1);
    on_spinAccount_valueChanged(1);
}

void MainWindow::on_spinAccount_valueChanged(int arg1)
{
    if (!root_set) return;
    // constants for Bitcoin
    const uint32_t version_public = 0x0488b21e;
    const uint32_t version_private = 0x0488ade4;
    const char addr_version = 0x00, wif_version = 0x80;
    const size_t buflen = 128;
    char buf[buflen + 1];
    HDNode node;
    uint32_t fingerprint;
    // external chain
    for (int chain = 0; chain < 2; chain++) {
        QTableWidget *list = chain == 0 ? ui->listAddress : ui->listChange;
        node = root;
        hdnode_private_ckd(&node, 44 | 0x80000000);
        hdnode_private_ckd(&node, 0 | 0x80000000); // bitcoin
        hdnode_private_ckd(&node, (arg1 - 1) | 0x80000000);
        fingerprint = hdnode_fingerprint(&node);
        hdnode_serialize_private(&node, fingerprint, version_private, buf, buflen); QString xprv = QString(buf); ui->lineXprv->setText(xprv);
        hdnode_serialize_public(&node, fingerprint, version_public, buf, buflen); QString xpub = QString(buf); ui->lineXpub->setText(xpub);
        hdnode_private_ckd(&node, chain); // external / internal
        for (int i = 0; i < 100; i++) {
            HDNode node2 = node;
            hdnode_private_ckd(&node2, i);
            hdnode_fill_public_key(&node2);
            ecdsa_get_address(node2.public_key, addr_version, buf, buflen); QString address = QString(buf);
            ecdsa_get_wif(node2.private_key, wif_version, buf, buflen); QString wif = QString(buf);
            list->setItem(i, 0, new QTableWidgetItem(address));
            list->setItem(i, 1, new QTableWidgetItem(wif));
            list->setItem(i, 2, new QTableWidgetItem("0.0"));
        }
    }
}
