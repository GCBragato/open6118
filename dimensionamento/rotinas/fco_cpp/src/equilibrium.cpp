#include "equilibrium.h"
#include <cmath>

namespace fco {

Esforcos integrar_concreto(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    double alpha, double x_LN, int n_grid)
{
    if (x_LN <= 0.0) return {0.0, 0.0, 0.0};

    const double eps_c2 = concreto.eps_c2_pmilh();
    const double eps_cu = concreto.eps_cu_pmilh();
    const double n_par = concreto.n_parabola();
    const double pico = concreto.pico_kncm2();        // 0,85*eta_c*fcd (FCO-01)
    const double pivo_c = concreto.pivo_c_rel();      // Figura 17.1 (FCO-02)

    const InclResult ir = h_inc_yp_max(secao, alpha);
    const double h_inc = ir.h_inc;
    const double yp_max = ir.yp_max;
    const double d_inc_ = d_inc(secao, alpha, yp_max);

    const double b = secao.base_cm;
    const double h = secao.altura_cm;
    const int nx = n_grid, ny = n_grid;
    const double dx = b / nx;
    const double dy = h / ny;
    const double dA = dx * dy;
    const double cos_a = std::cos(alpha);
    const double sin_a = std::sin(alpha);

    double Nc = 0.0, Mxc = 0.0, Myc = 0.0;

    // Loop x outer, y inner -> cache amigavel mas igual ao Python
    for (int i = 0; i < nx; ++i) {
        const double x = -b * 0.5 + dx * (i + 0.5);
        for (int j = 0; j < ny; ++j) {
            const double y = -h * 0.5 + dy * (j + 0.5);
            const double yp = -x * sin_a + y * cos_a;
            const double s = yp_max - yp;
            const double eps = strain_pmilh(s, x_LN, h_inc, d_inc_, eps_c2, eps_cu, pivo_c);
            const double sigma = sigma_concreto(eps, pico, eps_c2, n_par);
            Nc += sigma;
            Mxc += sigma * y;
            Myc += sigma * x;
        }
    }
    return {Nc * dA, Mxc * dA, Myc * dA};
}

Esforcos esforcos_barras(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double alpha, double x_LN)
{
    if (secao.barras.empty()) return {0.0, 0.0, 0.0};

    const double fyd = aco.fyd_kncm2();
    const double Es = aco.Es_kncm2;
    const double eps_yd = aco.eps_yd_pmilh();
    const double eps_c2 = concreto.eps_c2_pmilh();
    const double eps_cu = concreto.eps_cu_pmilh();
    const double n_par = concreto.n_parabola();
    const double pico = concreto.pico_kncm2();
    const double pivo_c = concreto.pivo_c_rel();

    if (x_LN <= 0.0) {
        // Tracao pura: todas barras eps -> -10 por mil
        double Ns = 0.0, Mxs = 0.0, Mys = 0.0;
        const double sig_s = sigma_aco(-EPS_SU, fyd, Es, eps_yd);
        for (const auto& b : secao.barras) {
            const double F = sig_s * b.area_cm2;
            Ns += F;
            Mxs += F * b.y_cm;
            Mys += F * b.x_cm;
        }
        return {Ns, Mxs, Mys};
    }

    const InclResult ir = h_inc_yp_max(secao, alpha);
    const double h_inc = ir.h_inc;
    const double yp_max = ir.yp_max;
    const double d_inc_ = d_inc(secao, alpha, yp_max);

    const double cos_a = std::cos(alpha);
    const double sin_a = std::sin(alpha);

    double Ns = 0.0, Mxs = 0.0, Mys = 0.0;
    for (const auto& b : secao.barras) {
        const double yp_b = -b.x_cm * sin_a + b.y_cm * cos_a;
        const double s_b = yp_max - yp_b;
        const double eps_b = strain_pmilh(s_b, x_LN, h_inc, d_inc_, eps_c2, eps_cu, pivo_c);
        const double sig_s = sigma_aco(eps_b, fyd, Es, eps_yd);
        const double sig_c = sigma_concreto(eps_b, pico, eps_c2, n_par);
        const double delta = sig_s - sig_c;
        const double F = delta * b.area_cm2;
        Ns += F;
        Mxs += F * b.y_cm;
        Mys += F * b.x_cm;
    }
    return {Ns, Mxs, Mys};
}

Esforcos esforcos_resistentes(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double alpha, double x_LN, int n_grid)
{
    Esforcos c = integrar_concreto(secao, concreto, alpha, x_LN, n_grid);
    Esforcos s = esforcos_barras(secao, concreto, aco, alpha, x_LN);
    return {c.N_kn + s.N_kn, c.Mx_kncm + s.Mx_kncm, c.My_kncm + s.My_kncm};
}

}  // namespace fco
