#pragma once
#include "geometry.h"
#include "constitutive.h"
#include "equilibrium.h"
#include <string>

namespace fco {

double Nd_max_kn(const SecaoRetangular& s, const Concreto& c, const Aco& a);
double Nd_min_kn(const SecaoRetangular& s, const Aco& a);

struct VerifResult {
    std::string status;       // "OK" | "NAO_VERIFICA" | "FORA_RANGE" | "NAO_CONVERGIU"
    double razao;             // MR / MS  (>= 1 OK)
    double alpha_rad;
    double x_LN_cm;
    double MRx_kncm;
    double MRy_kncm;
    double MR_kncm;
    std::string mensagem;
};

VerifResult verificar_fco(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double Nd_kn, double Mxd_kncm, double Myd_kncm,
    int n_grid = 60);

struct RadialResult {
    std::string status;
    double razao_dc;          // 1/lambda; <= 1 OK
    double lambda;
    std::string mensagem;
};

RadialResult razao_dc_radial(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double Nd_kn, double Mxd_kncm, double Myd_kncm,
    int n_grid = 60);

}  // namespace fco
