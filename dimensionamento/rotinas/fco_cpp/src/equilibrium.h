#pragma once
#include "geometry.h"
#include "constitutive.h"

namespace fco {

struct Esforcos {
    double N_kn;       // forca normal (compressao positiva)
    double Mx_kncm;    // momento em torno do eixo x
    double My_kncm;    // momento em torno do eixo y
};

// Integra concreto via grid 2D (n_grid x n_grid).
// secao centrada na origem; alpha = inclinacao da LN (rad).
Esforcos integrar_concreto(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    double alpha, double x_LN, int n_grid);

// Esforcos das barras: (sigma_aco - sigma_concreto) * As para nao
// duplicar contagem da area de concreto deslocada pelas barras.
Esforcos esforcos_barras(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double alpha, double x_LN);

// Total: concreto + barras.
Esforcos esforcos_resistentes(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double alpha, double x_LN, int n_grid);

}  // namespace fco
