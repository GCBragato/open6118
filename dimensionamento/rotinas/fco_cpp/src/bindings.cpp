#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "geometry.h"
#include "constitutive.h"
#include "equilibrium.h"
#include "solver.h"
#include "verifier.h"

namespace py = pybind11;
using namespace fco;

// Converte VerifResult / RadialResult / Esforcos em py::dict (mesmo formato
// retornado pelo Python original).
static py::dict verif_to_dict(const VerifResult& r) {
    py::dict d;
    d["status"] = r.status;
    d["razao"] = r.razao;
    d["alpha_rad"] = r.alpha_rad;
    d["alpha_graus"] = r.alpha_rad * 57.29577951308232;
    d["x_LN_cm"] = r.x_LN_cm;
    d["MRx_kncm"] = r.MRx_kncm;
    d["MRy_kncm"] = r.MRy_kncm;
    d["MR_kncm"] = r.MR_kncm;
    if (!r.mensagem.empty()) d["mensagem"] = r.mensagem;
    return d;
}

static py::dict radial_to_dict(const RadialResult& r) {
    py::dict d;
    d["status"] = r.status;
    d["razao_dc"] = r.razao_dc;
    d["lambda"] = r.lambda;
    if (!r.mensagem.empty()) d["mensagem"] = r.mensagem;
    return d;
}

PYBIND11_MODULE(_fco_native, m) {
    m.doc() = "FCO C++ native backend (open6118)";

    py::class_<Barra>(m, "Barra")
        .def(py::init<double, double, double>(),
             py::arg("x_cm"), py::arg("y_cm"), py::arg("area_cm2"))
        .def_readwrite("x_cm", &Barra::x_cm)
        .def_readwrite("y_cm", &Barra::y_cm)
        .def_readwrite("area_cm2", &Barra::area_cm2);

    py::class_<SecaoRetangular>(m, "SecaoRetangular")
        .def(py::init<>())
        .def(py::init([](double base, double altura, double cobr,
                         std::vector<Barra> bs) {
            SecaoRetangular s;
            s.base_cm = base;
            s.altura_cm = altura;
            s.cobrimento_cm = cobr;
            s.barras = std::move(bs);
            return s;
        }), py::arg("base_cm"), py::arg("altura_cm"),
            py::arg("cobrimento_cm") = 2.5,
            py::arg("barras") = std::vector<Barra>())
        .def_readwrite("base_cm", &SecaoRetangular::base_cm)
        .def_readwrite("altura_cm", &SecaoRetangular::altura_cm)
        .def_readwrite("cobrimento_cm", &SecaoRetangular::cobrimento_cm)
        .def_readwrite("barras", &SecaoRetangular::barras)
        .def_property_readonly("Ac_cm2", &SecaoRetangular::Ac_cm2)
        .def_property_readonly("As_total_cm2", &SecaoRetangular::As_total_cm2)
        .def_property_readonly("n_barras", &SecaoRetangular::n_barras);

    py::class_<Concreto>(m, "Concreto")
        .def(py::init([](double fck, double gama_c) {
            Concreto c; c.fck_mpa = fck; c.gama_c = gama_c; return c;
        }), py::arg("fck_mpa"), py::arg("gama_c") = 1.4)
        .def_readwrite("fck_mpa", &Concreto::fck_mpa)
        .def_readwrite("gama_c", &Concreto::gama_c)
        .def_property_readonly("fcd_kncm2", &Concreto::fcd_kncm2)
        .def_property_readonly("eps_c2_pmilh", &Concreto::eps_c2_pmilh)
        .def_property_readonly("eps_cu_pmilh", &Concreto::eps_cu_pmilh)
        .def_property_readonly("n_parabola", &Concreto::n_parabola);

    py::class_<Aco>(m, "Aco")
        .def(py::init([](double fyk, double Es, double gama_s) {
            Aco a; a.fyk_mpa = fyk; a.Es_kncm2 = Es; a.gama_s = gama_s; return a;
        }), py::arg("fyk_mpa") = 500.0, py::arg("Es_kncm2") = 21000.0,
            py::arg("gama_s") = 1.15)
        .def_readwrite("fyk_mpa", &Aco::fyk_mpa)
        .def_readwrite("Es_kncm2", &Aco::Es_kncm2)
        .def_readwrite("gama_s", &Aco::gama_s)
        .def_property_readonly("fyd_kncm2", &Aco::fyd_kncm2)
        .def_property_readonly("eps_yd_pmilh", &Aco::eps_yd_pmilh);

    m.def("Nd_max_kn", &Nd_max_kn);
    m.def("Nd_min_kn", &Nd_min_kn);

    m.def("esforcos_resistentes",
          [](const SecaoRetangular& s, const Concreto& c, const Aco& a,
             double alpha, double x_LN, int n_grid) {
              auto e = esforcos_resistentes(s, c, a, alpha, x_LN, n_grid);
              return py::make_tuple(e.N_kn, e.Mx_kncm, e.My_kncm);
          },
          py::arg("secao"), py::arg("concreto"), py::arg("aco"),
          py::arg("alpha"), py::arg("x_LN"), py::arg("n_grid") = 80);

    m.def("verificar_fco",
          [](const SecaoRetangular& s, const Concreto& c, const Aco& a,
             double Nd, double Mxd, double Myd, int n_grid) {
              return verif_to_dict(verificar_fco(s, c, a, Nd, Mxd, Myd, n_grid));
          },
          py::arg("secao"), py::arg("concreto"), py::arg("aco"),
          py::arg("Nd_kn"), py::arg("Mxd_kncm"), py::arg("Myd_kncm"),
          py::arg("n_grid") = 60);

    m.def("razao_dc_radial",
          [](const SecaoRetangular& s, const Concreto& c, const Aco& a,
             double Nd, double Mxd, double Myd, int n_grid) {
              return radial_to_dict(razao_dc_radial(s, c, a, Nd, Mxd, Myd, n_grid));
          },
          py::arg("secao"), py::arg("concreto"), py::arg("aco"),
          py::arg("Nd_kn"), py::arg("Mxd_kncm"), py::arg("Myd_kncm"),
          py::arg("n_grid") = 60);
}
