"""Tushare backend implemented with the Tushare Pro API."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable, Mapping, cast

import pandas as pd
import pyarrow as pa

from ..exceptions import (
    BackendConnectionError,
    DatasetRegistrationError,
    InvalidQueryError,
    RemoteQueryError,
    SchemaMismatchError,
)
from ..models import (
    DataQuery,
    DatasetContract,
    DatasetDefinition,
    RegisteredDataset,
    TushareConfig,
    TushareDatasetSpec,
)
from .tushare_catalog import (
    DateRangeQuery,
    DisclosureSemantics,
    MembershipQuery,
    MembershipSemantics,
    PeriodQuery,
    TushareApiRoute,
    TushareDatasetCatalog,
    build_tushare_catalogs,
)

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_QUARTER_ENDS = ((3, 31), (6, 30), (9, 30), (12, 31))

_INCOME_DEFAULT_FIELDS = (
    "ts_code",
    "ann_date",
    "f_ann_date",
    "end_date",
    "report_type",
    "comp_type",
    "end_type",
    "basic_eps",
    "diluted_eps",
    "total_revenue",
    "revenue",
    "int_income",
    "prem_earned",
    "comm_income",
    "n_commis_income",
    "n_oth_income",
    "n_oth_b_income",
    "prem_income",
    "out_prem",
    "une_prem_reser",
    "reins_income",
    "n_sec_tb_income",
    "n_sec_uw_income",
    "n_asset_mg_income",
    "oth_b_income",
    "fv_value_chg_gain",
    "invest_income",
    "ass_invest_income",
    "forex_gain",
    "total_cogs",
    "oper_cost",
    "int_exp",
    "comm_exp",
    "biz_tax_surchg",
    "sell_exp",
    "admin_exp",
    "fin_exp",
    "assets_impair_loss",
    "prem_refund",
    "compens_payout",
    "reser_insur_liab",
    "div_payt",
    "reins_exp",
    "oper_exp",
    "compens_payout_refu",
    "insur_reser_refu",
    "reins_cost_refund",
    "other_bus_cost",
    "operate_profit",
    "non_oper_income",
    "non_oper_exp",
    "nca_disploss",
    "total_profit",
    "income_tax",
    "n_income",
    "n_income_attr_p",
    "minority_gain",
    "oth_compr_income",
    "t_compr_income",
    "compr_inc_attr_p",
    "compr_inc_attr_m_s",
    "ebit",
    "ebitda",
    "insurance_exp",
    "undist_profit",
    "distable_profit",
    "rd_exp",
    "fin_exp_int_exp",
    "fin_exp_int_inc",
    "transfer_surplus_rese",
    "transfer_housing_imprest",
    "transfer_oth",
    "adj_lossgain",
    "withdra_legal_surplus",
    "withdra_legal_pubfund",
    "withdra_biz_devfund",
    "withdra_rese_fund",
    "withdra_oth_ersu",
    "workers_welfare",
    "distr_profit_shrhder",
    "prfshare_payable_dvd",
    "comshare_payable_dvd",
    "capit_comstock_div",
    "continued_net_profit",
    "update_flag",
)
_FINANCE_DATE_FIELDS = frozenset(
    {"ann_date", "f_ann_date", "end_date", "first_ann_date", "begin_date", "close_date"}
)
_FINANCE_STRING_FIELDS = frozenset(
    {
        "ts_code",
        "report_type",
        "comp_type",
        "end_type",
        "update_flag",
        "type",
        "summary",
        "change_reason",
        "perf_summary",
        "remark",
        "holder_name",
        "holder_type",
        "in_de",
    }
)
_FINANCE_INTEGER_FIELDS = frozenset({"is_audit", "holder_num"})

_BALANCESHEET_DEFAULT_FIELDS = (
    "ts_code",
    "ann_date",
    "f_ann_date",
    "end_date",
    "report_type",
    "comp_type",
    "end_type",
    "total_share",
    "cap_rese",
    "undistr_porfit",
    "surplus_rese",
    "special_rese",
    "money_cap",
    "trad_asset",
    "notes_receiv",
    "accounts_receiv",
    "oth_receiv",
    "prepayment",
    "div_receiv",
    "int_receiv",
    "inventories",
    "amor_exp",
    "nca_within_1y",
    "sett_rsrv",
    "loanto_oth_bank_fi",
    "premium_receiv",
    "reinsur_receiv",
    "reinsur_res_receiv",
    "pur_resale_fa",
    "oth_cur_assets",
    "total_cur_assets",
    "fa_avail_for_sale",
    "htm_invest",
    "lt_eqt_invest",
    "invest_real_estate",
    "time_deposits",
    "oth_assets",
    "lt_rec",
    "fix_assets",
    "cip",
    "const_materials",
    "fixed_assets_disp",
    "produc_bio_assets",
    "oil_and_gas_assets",
    "intan_assets",
    "r_and_d",
    "goodwill",
    "lt_amor_exp",
    "defer_tax_assets",
    "decr_in_disbur",
    "oth_nca",
    "total_nca",
    "cash_reser_cb",
    "depos_in_oth_bfi",
    "prec_metals",
    "deriv_assets",
    "rr_reins_une_prem",
    "rr_reins_outstd_cla",
    "rr_reins_lins_liab",
    "rr_reins_lthins_liab",
    "refund_depos",
    "ph_pledge_loans",
    "refund_cap_depos",
    "indep_acct_assets",
    "client_depos",
    "client_prov",
    "transac_seat_fee",
    "invest_as_receiv",
    "total_assets",
    "lt_borr",
    "st_borr",
    "cb_borr",
    "depos_ib_deposits",
    "loan_oth_bank",
    "trading_fl",
    "notes_payable",
    "acct_payable",
    "adv_receipts",
    "sold_for_repur_fa",
    "comm_payable",
    "payroll_payable",
    "taxes_payable",
    "int_payable",
    "div_payable",
    "oth_payable",
    "acc_exp",
    "deferred_inc",
    "st_bonds_payable",
    "payable_to_reinsurer",
    "rsrv_insur_cont",
    "acting_trading_sec",
    "acting_uw_sec",
    "non_cur_liab_due_1y",
    "oth_cur_liab",
    "total_cur_liab",
    "bond_payable",
    "lt_payable",
    "specific_payables",
    "estimated_liab",
    "defer_tax_liab",
    "defer_inc_non_cur_liab",
    "oth_ncl",
    "total_ncl",
    "depos_oth_bfi",
    "deriv_liab",
    "depos",
    "agency_bus_liab",
    "oth_liab",
    "prem_receiv_adva",
    "depos_received",
    "ph_invest",
    "reser_une_prem",
    "reser_outstd_claims",
    "reser_lins_liab",
    "reser_lthins_liab",
    "indept_acc_liab",
    "pledge_borr",
    "indem_payable",
    "policy_div_payable",
    "total_liab",
    "treasury_share",
    "ordin_risk_reser",
    "forex_differ",
    "invest_loss_unconf",
    "minority_int",
    "total_hldr_eqy_exc_min_int",
    "total_hldr_eqy_inc_min_int",
    "total_liab_hldr_eqy",
    "lt_payroll_payable",
    "oth_comp_income",
    "oth_eqt_tools",
    "oth_eqt_tools_p_shr",
    "lending_funds",
    "acc_receivable",
    "st_fin_payable",
    "payables",
    "hfs_assets",
    "hfs_sales",
    "cost_fin_assets",
    "fair_value_fin_assets",
    "cip_total",
    "oth_pay_total",
    "long_pay_total",
    "debt_invest",
    "oth_debt_invest",
    "contract_assets",
    "contract_liab",
    "accounts_receiv_bill",
    "accounts_pay",
    "oth_rcv_total",
    "fix_assets_total",
    "update_flag",
)

_CASHFLOW_DEFAULT_FIELDS = (
    "ts_code",
    "ann_date",
    "f_ann_date",
    "end_date",
    "comp_type",
    "report_type",
    "end_type",
    "net_profit",
    "finan_exp",
    "c_fr_sale_sg",
    "recp_tax_rends",
    "n_depos_incr_fi",
    "n_incr_loans_cb",
    "n_inc_borr_oth_fi",
    "prem_fr_orig_contr",
    "n_incr_insured_dep",
    "n_reinsur_prem",
    "n_incr_disp_tfa",
    "ifc_cash_incr",
    "n_incr_disp_faas",
    "n_incr_loans_oth_bank",
    "n_cap_incr_repur",
    "c_fr_oth_operate_a",
    "c_inf_fr_operate_a",
    "c_paid_goods_s",
    "c_paid_to_for_empl",
    "c_paid_for_taxes",
    "n_incr_clt_loan_adv",
    "n_incr_dep_cbob",
    "c_pay_claims_orig_inco",
    "pay_handling_chrg",
    "pay_comm_insur_plcy",
    "oth_cash_pay_oper_act",
    "st_cash_out_act",
    "n_cashflow_act",
    "oth_recp_ral_inv_act",
    "c_disp_withdrwl_invest",
    "c_recp_return_invest",
    "n_recp_disp_fiolta",
    "n_recp_disp_sobu",
    "stot_inflows_inv_act",
    "c_pay_acq_const_fiolta",
    "c_paid_invest",
    "n_disp_subs_oth_biz",
    "oth_pay_ral_inv_act",
    "n_incr_pledge_loan",
    "stot_out_inv_act",
    "n_cashflow_inv_act",
    "c_recp_borrow",
    "proc_issue_bonds",
    "oth_cash_recp_ral_fnc_act",
    "stot_cash_in_fnc_act",
    "free_cashflow",
    "c_prepay_amt_borr",
    "c_pay_dist_dpcp_int_exp",
    "incl_dvd_profit_paid_sc_ms",
    "oth_cashpay_ral_fnc_act",
    "stot_cashout_fnc_act",
    "n_cash_flows_fnc_act",
    "eff_fx_flu_cash",
    "n_incr_cash_cash_equ",
    "c_cash_equ_beg_period",
    "c_cash_equ_end_period",
    "c_recp_cap_contrib",
    "incl_cash_rec_saims",
    "uncon_invest_loss",
    "prov_depr_assets",
    "depr_fa_coga_dpba",
    "amort_intang_assets",
    "lt_amort_deferred_exp",
    "decr_deferred_exp",
    "incr_acc_exp",
    "loss_disp_fiolta",
    "loss_scr_fa",
    "loss_fv_chg",
    "invest_loss",
    "decr_def_inc_tax_assets",
    "incr_def_inc_tax_liab",
    "decr_inventories",
    "decr_oper_payable",
    "incr_oper_payable",
    "others",
    "im_net_cashflow_oper_act",
    "conv_debt_into_cap",
    "conv_copbonds_due_within_1y",
    "fa_fnc_leases",
    "im_n_incr_cash_equ",
    "net_dism_capital_add",
    "net_cash_rece_sec",
    "credit_impa_loss",
    "use_right_asset_dep",
    "oth_loss_asset",
    "end_bal_cash",
    "beg_bal_cash",
    "end_bal_cash_equ",
    "beg_bal_cash_equ",
    "update_flag",
)

_FINA_INDICATOR_DEFAULT_FIELDS = (
    "ts_code",
    "ann_date",
    "end_date",
    "eps",
    "dt_eps",
    "total_revenue_ps",
    "revenue_ps",
    "capital_rese_ps",
    "surplus_rese_ps",
    "undist_profit_ps",
    "extra_item",
    "profit_dedt",
    "gross_margin",
    "current_ratio",
    "quick_ratio",
    "cash_ratio",
    "invturn_days",
    "arturn_days",
    "inv_turn",
    "ar_turn",
    "ca_turn",
    "fa_turn",
    "assets_turn",
    "op_income",
    "valuechange_income",
    "interst_income",
    "daa",
    "ebit",
    "ebitda",
    "fcff",
    "fcfe",
    "current_exint",
    "noncurrent_exint",
    "interestdebt",
    "netdebt",
    "tangible_asset",
    "working_capital",
    "networking_capital",
    "invest_capital",
    "retained_earnings",
    "diluted2_eps",
    "bps",
    "ocfps",
    "retainedps",
    "cfps",
    "ebit_ps",
    "fcff_ps",
    "fcfe_ps",
    "netprofit_margin",
    "grossprofit_margin",
    "cogs_of_sales",
    "expense_of_sales",
    "profit_to_gr",
    "saleexp_to_gr",
    "adminexp_of_gr",
    "finaexp_of_gr",
    "impai_ttm",
    "gc_of_gr",
    "op_of_gr",
    "ebit_of_gr",
    "roe",
    "roe_waa",
    "roe_dt",
    "roa",
    "npta",
    "roic",
    "roe_yearly",
    "roa2_yearly",
    "roe_avg",
    "opincome_of_ebt",
    "investincome_of_ebt",
    "n_op_profit_of_ebt",
    "tax_to_ebt",
    "dtprofit_to_profit",
    "salescash_to_or",
    "ocf_to_or",
    "ocf_to_opincome",
    "capitalized_to_da",
    "debt_to_assets",
    "assets_to_eqt",
    "dp_assets_to_eqt",
    "ca_to_assets",
    "nca_to_assets",
    "tbassets_to_totalassets",
    "int_to_talcap",
    "eqt_to_talcapital",
    "currentdebt_to_debt",
    "longdeb_to_debt",
    "ocf_to_shortdebt",
    "debt_to_eqt",
    "eqt_to_debt",
    "eqt_to_interestdebt",
    "tangibleasset_to_debt",
    "tangasset_to_intdebt",
    "tangibleasset_to_netdebt",
    "ocf_to_debt",
    "ocf_to_interestdebt",
    "ocf_to_netdebt",
    "ebit_to_interest",
    "longdebt_to_workingcapital",
    "ebitda_to_debt",
    "turn_days",
    "roa_yearly",
    "roa_dp",
    "fixed_assets",
    "profit_prefin_exp",
    "non_op_profit",
    "op_to_ebt",
    "nop_to_ebt",
    "ocf_to_profit",
    "cash_to_liqdebt",
    "cash_to_liqdebt_withinterest",
    "op_to_liqdebt",
    "op_to_debt",
    "roic_yearly",
    "total_fa_trun",
    "profit_to_op",
    "q_opincome",
    "q_investincome",
    "q_dtprofit",
    "q_eps",
    "q_netprofit_margin",
    "q_gsprofit_margin",
    "q_exp_to_sales",
    "q_profit_to_gr",
    "q_saleexp_to_gr",
    "q_adminexp_to_gr",
    "q_finaexp_to_gr",
    "q_impair_to_gr_ttm",
    "q_gc_to_gr",
    "q_op_to_gr",
    "q_roe",
    "q_dt_roe",
    "q_npta",
    "q_opincome_to_ebt",
    "q_investincome_to_ebt",
    "q_dtprofit_to_profit",
    "q_salescash_to_or",
    "q_ocf_to_sales",
    "q_ocf_to_or",
    "basic_eps_yoy",
    "dt_eps_yoy",
    "cfps_yoy",
    "op_yoy",
    "ebt_yoy",
    "netprofit_yoy",
    "dt_netprofit_yoy",
    "ocf_yoy",
    "roe_yoy",
    "bps_yoy",
    "assets_yoy",
    "eqt_yoy",
    "tr_yoy",
    "or_yoy",
    "q_gr_yoy",
    "q_gr_qoq",
    "q_sales_yoy",
    "q_sales_qoq",
    "q_op_yoy",
    "q_op_qoq",
    "q_profit_yoy",
    "q_profit_qoq",
    "q_netprofit_yoy",
    "q_netprofit_qoq",
    "equity_yoy",
    "rd_exp",
    "update_flag",
)

_EXPRESS_DEFAULT_FIELDS = (
    "ts_code",
    "ann_date",
    "end_date",
    "revenue",
    "operate_profit",
    "total_profit",
    "n_income",
    "total_assets",
    "total_hldr_eqy_exc_min_int",
    "diluted_eps",
    "diluted_roe",
    "yoy_net_profit",
    "bps",
    "yoy_sales",
    "yoy_op",
    "yoy_tp",
    "yoy_dedu_np",
    "yoy_eps",
    "yoy_roe",
    "growth_assets",
    "yoy_equity",
    "growth_bps",
    "or_last_year",
    "op_last_year",
    "tp_last_year",
    "np_last_year",
    "eps_last_year",
    "open_net_assets",
    "open_bps",
    "perf_summary",
    "is_audit",
    "remark",
)

_FORECAST_DEFAULT_FIELDS = (
    "ts_code",
    "ann_date",
    "end_date",
    "type",
    "p_change_min",
    "p_change_max",
    "net_profit_min",
    "net_profit_max",
    "last_parent_net",
    "first_ann_date",
    "summary",
    "change_reason",
)

_STK_HOLDERNUMBER_DEFAULT_FIELDS = (
    "ts_code",
    "ann_date",
    "end_date",
    "holder_num",
)

_STK_HOLDERTRADE_DEFAULT_FIELDS = (
    "ts_code",
    "ann_date",
    "holder_name",
    "holder_type",
    "in_de",
    "change_vol",
    "change_ratio",
    "after_share",
    "after_ratio",
    "avg_price",
    "total_share",
    "begin_date",
    "close_date",
)

_INDUSTRY_MEMBER_FIELDS = (
    "l1_code",
    "l1_name",
    "l2_code",
    "l2_name",
    "l3_code",
    "l3_name",
    "ts_code",
    "name",
    "in_date",
    "out_date",
    "is_new",
)
_INDUSTRY_MEMBER_DATE_FIELDS = frozenset({"in_date", "out_date"})


@dataclass(frozen=True, slots=True)
class TushareSource:
    """Store prepared Tushare source metadata.

    Parameters
    ----------
    connection
        Named Tushare connection profile.
    dataset
        Logical catalog dataset name.
    schema_hash
        Stable hash of the catalog schema.
    fixed_params
        Sanitized constant API parameters from the dataset specification.
    """

    connection: str
    dataset: str
    schema_hash: str
    fixed_params: Mapping[str, object]


def _financial_statement_schema(field_names: tuple[str, ...]) -> pa.Schema:
    fields: list[pa.Field] = []
    for name in field_names:
        if name in _FINANCE_DATE_FIELDS:
            data_type = pa.date32()
        elif name in _FINANCE_STRING_FIELDS:
            data_type = pa.string()
        elif name in _FINANCE_INTEGER_FIELDS:
            data_type = pa.int64()
        else:
            data_type = pa.float64()
        fields.append(pa.field(name, data_type))
    return pa.schema(fields)


def _industry_member_schema(field_names: tuple[str, ...]) -> pa.Schema:
    fields: list[pa.Field] = []
    for name in field_names:
        data_type = pa.date32() if name in _INDUSTRY_MEMBER_DATE_FIELDS else pa.string()
        fields.append(pa.field(name, data_type))
    return pa.schema(fields)


_INCOME_SCHEMA = _financial_statement_schema(_INCOME_DEFAULT_FIELDS)
_BALANCESHEET_SCHEMA = _financial_statement_schema(_BALANCESHEET_DEFAULT_FIELDS)
_CASHFLOW_SCHEMA = _financial_statement_schema(_CASHFLOW_DEFAULT_FIELDS)
_FINA_INDICATOR_SCHEMA = _financial_statement_schema(_FINA_INDICATOR_DEFAULT_FIELDS)
_EXPRESS_SCHEMA = _financial_statement_schema(_EXPRESS_DEFAULT_FIELDS)
_FORECAST_SCHEMA = _financial_statement_schema(_FORECAST_DEFAULT_FIELDS)
_STK_HOLDERNUMBER_SCHEMA = _financial_statement_schema(_STK_HOLDERNUMBER_DEFAULT_FIELDS)
_STK_HOLDERTRADE_SCHEMA = _financial_statement_schema(_STK_HOLDERTRADE_DEFAULT_FIELDS)
_INDUSTRY_MEMBER_SCHEMA = _industry_member_schema(_INDUSTRY_MEMBER_FIELDS)
_TUSHARE_DATASETS = build_tushare_catalogs(
    {
        "income": _INCOME_SCHEMA,
        "balancesheet": _BALANCESHEET_SCHEMA,
        "cashflow": _CASHFLOW_SCHEMA,
        "fina_indicator": _FINA_INDICATOR_SCHEMA,
        "express": _EXPRESS_SCHEMA,
        "forecast": _FORECAST_SCHEMA,
        "stk_holdernumber": _STK_HOLDERNUMBER_SCHEMA,
        "stk_holdertrade": _STK_HOLDERTRADE_SCHEMA,
        "industry_member": _INDUSTRY_MEMBER_SCHEMA,
    }
)


class TushareBackend:
    """Query catalog-backed Tushare APIs and normalize them to Arrow.

    Parameters
    ----------
    client_factory
        Optional callable receiving ``token=...`` and returning a Tushare-like
        client. It supports deterministic tests without the Tushare package or
        network access.

    Notes
    -----
    The catalog defines schemas, deterministic API routes, table identity
    columns, panel compatibility, disclosure state rules, and membership
    intervals.
    Trading calendars are cached per connection, exchange, year, and month.
    """

    def __init__(self, client_factory: Callable[..., Any] | None = None) -> None:
        self._configs: dict[str, TushareConfig] = {}
        self._clients: dict[str, Any] = {}
        self._client_factory = client_factory
        self._calendar_cache: dict[tuple[str, str, int, int], list[date]] = {}

    def add_connection(self, name: str, config: TushareConfig) -> None:
        """Add or replace a validated Tushare connection profile.

        Parameters
        ----------
        name
            Identifier used by dataset specifications.
        config
            Direct token or token-environment configuration.

        Raises
        ------
        DatasetRegistrationError
            If the name or token configuration is invalid.

        Notes
        -----
        The token environment variable is not read here. Replacing an
        initialized profile closes its cached client.
        """

        if not name or not _IDENTIFIER.fullmatch(name):
            raise DatasetRegistrationError(f"Invalid Tushare connection name: {name!r}")
        if config.token is not None and not config.token:
            raise DatasetRegistrationError("Tushare token cannot be empty")
        if config.token_env is not None and not config.token_env:
            raise DatasetRegistrationError("Tushare token environment variable cannot be empty")
        if config.token is None and config.token_env is None:
            raise DatasetRegistrationError("Tushare token or token_env must be configured")
        existing = self._clients.pop(name, None)
        if existing is not None:
            self._close_client(existing)
        self._configs[name] = config

    def prepare(self, definition: DatasetDefinition) -> RegisteredDataset:
        """Prepare a logical catalog-backed Tushare dataset without connecting.

        Parameters
        ----------
        definition
            Tushare dataset specification referencing a configured profile and
            logical catalog name.

        Returns
        -------
        RegisteredDataset
            Normalized specification, catalog schema, and source metadata.

        Raises
        ------
        DatasetRegistrationError
            If the definition, catalog name, profile, columns, or fixed parameters
            are invalid.

        Notes
        -----
        Preparation is fully offline. Tokens and clients are resolved lazily on
        the first query.
        """

        if not isinstance(definition, TushareDatasetSpec):
            raise DatasetRegistrationError("Tushare backend requires TushareDatasetSpec")
        logical_name = definition.dataset or definition.name
        catalog = self._catalog(logical_name)
        self._validate_definition(definition, catalog)
        if definition.connection not in self._configs:
            raise DatasetRegistrationError(
                f"Tushare connection {definition.connection!r} is not configured"
            )
        normalized = json.dumps(
            [(field.name, str(field.type)) for field in catalog.schema],
            separators=(",", ":"),
        )
        source = TushareSource(
            definition.connection,
            catalog.name,
            hashlib.sha256(normalized.encode()).hexdigest(),
            dict(definition.fixed_params),
        )
        return RegisteredDataset(
            spec=definition,
            schema=catalog.schema,
            source=source,
            contract=self._contract(definition, catalog),
        )

    def scan(self, dataset: RegisteredDataset, query: DataQuery) -> pa.Table:
        """Fetch a normalized, lossless Tushare long table.

        Parameters
        ----------
        dataset
            Prepared Tushare dataset.
        query
            Normalized fields, closed time range, stock universe, and limit.

        Returns
        -------
        pyarrow.Table
            Typed, ordered long table retaining every returned source row.

        Raises
        ------
        InvalidQueryError
            If the API requires instruments or time bounds that are missing.
        RemoteQueryError
            If a Tushare or calendar call fails or returns an invalid object.
        SchemaMismatchError
            If returned columns, values, or prepared state conflict with the
            catalog.

        Notes
        -----
        Quarterly APIs are called per report period. Membership datasets return
        raw effective-dated intervals; only panel queries expand them.
        """

        _, source, catalog = self._state(dataset)
        selected = self.table_columns(dataset, query.fields)
        if query.instruments == ():
            return self._empty_arrow(catalog.schema, selected)
        route = self._select_route(catalog, query.instruments)
        client = self._client(source.connection)
        remote_fields = self._remote_columns(selected, catalog)
        frames = self._fetch_table_frames(
            client, source.fixed_params, route, query, remote_fields
        )
        frame = self._normalize_remote_frames(frames, catalog, remote_fields, route)
        semantics = catalog.semantics
        if isinstance(semantics, DisclosureSemantics):
            frame = self._filter_time(frame, semantics.period_column, query)
        elif isinstance(semantics, MembershipSemantics):
            frame = self._filter_membership_overlap(frame, semantics, query)
        else:
            frame = self._filter_time(frame, semantics.table_time_column, query)
        frame = self._sort_by(frame, semantics.table_order)
        if query.limit is not None:
            frame = frame.head(query.limit)
        return self._frame_to_arrow(frame, catalog.schema, selected)

    def scan_disclosure_events(
        self, dataset: RegisteredDataset, query: DataQuery
    ) -> pa.Table:
        """Fetch disclosure events required by a point-in-time panel.

        Parameters
        ----------
        dataset
            Prepared logical disclosure dataset.
        query
            Panel request with both time bounds.

        Returns
        -------
        pyarrow.Table
            Disclosure, instrument, period, and requested field columns ordered
            by disclosure chronology.

        Raises
        ------
        InvalidQueryError
            If bounds, instruments, or disclosure-range parameters are not
            available for the selected API.
        RemoteQueryError
            If a remote request fails.
        SchemaMismatchError
            If the response conflicts with the catalog schema.

        Notes
        -----
        The fetch starts ``fetch_buffer_days`` before the requested panel to
        carry previously disclosed values into its left boundary. All revisions
        are retained for the point-in-time state machine.
        """

        spec, source, catalog = self._state(dataset)
        if query.start is None or query.end is None:
            raise InvalidQueryError(
                f"Dataset {spec.name!r} point-in-time panel requires both start and end"
            )
        semantics = catalog.semantics
        if not isinstance(semantics, DisclosureSemantics):
            raise InvalidQueryError(
                f"Tushare dataset {catalog.name!r} is not disclosure data"
            )
        route = self._select_route(catalog, query.instruments)
        if route.disclosure_query is None:
            raise InvalidQueryError(
                f"Tushare api {route.api_name!r} cannot serve a point-in-time panel"
            )
        client = self._client(source.connection)
        selected = self._unique_columns(
            (
                semantics.disclosure_column,
                catalog.instrument_column,
                semantics.period_column,
                *semantics.identity_columns,
                *query.fields,
            )
        )
        remote_fields = self._remote_columns(selected, catalog)
        fetch_start = query.start - timedelta(days=spec.fetch_buffer_days)
        fetch_query = DataQuery(
            query.fields,
            fetch_start,
            query.end,
            query.instruments,
            None,
        )
        frames = self._fetch_disclosure_route_frames(
            client, source.fixed_params, route, fetch_query, remote_fields
        )
        frame = self._normalize_remote_frames(
            frames, catalog, remote_fields, route
        )
        frame = self._filter_time(frame, semantics.disclosure_column, fetch_query)
        frame = self._sort_by(
            frame,
            self._unique_columns(
                (
                    semantics.disclosure_column,
                    catalog.instrument_column,
                    semantics.period_column,
                    *semantics.revision_order,
                )
            ),
        )
        return self._frame_to_arrow(frame, catalog.schema, selected)

    def trade_calendar(self, dataset: RegisteredDataset, query: DataQuery) -> list[date]:
        """Return the buffered trading calendar for a PIT panel.

        Parameters
        ----------
        dataset
            Prepared Tushare dataset.
        query
            Panel query with both time bounds.

        Returns
        -------
        list[datetime.date]
            Open sessions from the buffered start through the margin-adjusted
            end date.

        Raises
        ------
        InvalidQueryError
            If either time bound is missing.
        RemoteQueryError
            If ``trade_cal`` fails or omits its date column.
        """

        spec, source, _ = self._state(dataset)
        if query.start is None or query.end is None:
            raise InvalidQueryError(
                f"Dataset {spec.name!r} panel requires both start and end"
            )
        start = query.start - timedelta(days=spec.fetch_buffer_days)
        end = query.end + timedelta(days=spec.fetch_margin_days)
        return self._fetch_calendar(source.connection, spec.calendar_exchange, start, end)

    def pit_panel_semantics(
        self, dataset: RegisteredDataset
    ) -> tuple[str, str, tuple[str, ...]]:
        """Return disclosure, report-period, and revision precedence columns.

        Parameters
        ----------
        dataset
            Prepared Tushare dataset.

        Returns
        -------
        tuple[str, str, tuple[str, ...]]
            Disclosure column, period column, and ordered revision columns.
        """

        _, _, catalog = self._state(dataset)
        semantics = catalog.semantics
        if not isinstance(semantics, DisclosureSemantics):
            raise SchemaMismatchError(
                f"Tushare dataset {catalog.name!r} is not disclosure data"
            )
        return (
            semantics.disclosure_column,
            semantics.period_column,
            semantics.revision_order,
        )

    def fingerprint(self, dataset: RegisteredDataset) -> dict[str, object]:
        """Return sanitized API and schema provenance.

        Parameters
        ----------
        dataset
            Prepared Tushare dataset.

        Returns
        -------
        dict[str, object]
            JSON-serializable connection name, API, schema hash, and stringified
            fixed parameters. Tokens are excluded.
        """

        _, source, catalog = self._state(dataset)
        return {
            "backend": "tushare",
            "connection": source.connection,
            "dataset": source.dataset,
            "available_apis": [route.api_name for route in catalog.routes],
            "schema_hash": source.schema_hash,
            "fixed_params": {str(key): str(value) for key, value in source.fixed_params.items()},
        }

    def route_name(
        self, dataset: RegisteredDataset, query: DataQuery
    ) -> str | None:
        """Return the deterministic data API selected for audit metadata."""

        _, _, catalog = self._state(dataset)
        if query.instruments == ():
            return None
        return self._select_route(catalog, query.instruments).api_name

    def panel_kind(self, dataset: RegisteredDataset) -> str:
        """Return ``disclosure``, ``membership``, or ``event`` panel semantics."""

        _, _, catalog = self._state(dataset)
        if isinstance(catalog.semantics, DisclosureSemantics):
            return "disclosure"
        if isinstance(catalog.semantics, MembershipSemantics):
            return "membership"
        return "event"

    def table_columns(
        self, dataset: RegisteredDataset, fields: tuple[str, ...]
    ) -> tuple[str, ...]:
        """Return ordered table keys, automatic identity columns, and fields."""

        contract = dataset.contract
        return self._unique_columns(
            (
                contract.table_time_column,
                contract.instrument_column,
                *contract.table_identity_columns,
                *fields,
            )
        )

    def scan_membership_panel(
        self, dataset: RegisteredDataset, query: DataQuery
    ) -> pa.Table:
        """Expand raw membership intervals over the requested trading calendar."""

        spec, source, catalog = self._state(dataset)
        semantics = catalog.semantics
        if not isinstance(semantics, MembershipSemantics):
            raise SchemaMismatchError(
                f"Tushare dataset {catalog.name!r} is not membership data"
            )
        if query.start is None or query.end is None:
            raise InvalidQueryError(
                f"Dataset {spec.name!r} membership panel requires both start and end"
            )
        selected_raw = self._unique_columns(
            (
                semantics.interval_start_column,
                catalog.instrument_column,
                semantics.interval_end_column,
                *semantics.identity_columns,
                *query.fields,
            )
        )
        route = self._select_route(catalog, query.instruments)
        remote_fields = self._remote_columns(selected_raw, catalog)
        if query.instruments == ():
            frames: list[pd.DataFrame] = []
        else:
            frames = self._fetch_table_frames(
                self._client(source.connection),
                source.fixed_params,
                route,
                query,
                remote_fields,
            )
        raw = self._normalize_remote_frames(frames, catalog, remote_fields, route)
        raw = self._filter_membership_overlap(raw, semantics, query)
        calendar = self._fetch_calendar(
            source.connection,
            spec.calendar_exchange,
            query.start,
            query.end,
        )
        selected_panel = self._unique_columns(
            (
                semantics.panel_time_column,
                catalog.instrument_column,
                *query.fields,
            )
        )
        expanded = self._expand_membership_panel(
            raw,
            semantics,
            catalog.instrument_column,
            query,
            calendar,
            selected_panel,
        )
        return self._membership_frame_to_arrow(
            expanded,
            catalog.schema,
            semantics.panel_time_column,
            selected_panel,
        )

    def close(self) -> None:
        """Close cached Tushare clients and clear calendar entries."""

        for client in self._clients.values():
            self._close_client(client)
        self._clients.clear()
        self._calendar_cache.clear()

    def _client(self, name: str) -> Any:
        existing = self._clients.get(name)
        if existing is not None:
            return existing
        config = self._configs.get(name)
        if config is None:
            raise DatasetRegistrationError(f"Tushare connection {name!r} is not configured")
        token = config.token
        if token is None and config.token_env:
            token = os.environ.get(config.token_env)
            if token is None:
                raise BackendConnectionError(
                    f"Tushare token environment variable {config.token_env!r} is not set"
                )
        if token is None:
            raise BackendConnectionError("Tushare token is not configured")
        factory = self._client_factory
        if factory is None:
            try:
                import tushare as ts
            except ImportError as exc:
                raise BackendConnectionError(
                    "Tushare support is not installed; install the tushare package"
                ) from exc
            try:
                ts_module = cast(Any, ts)
                ts_module.set_token(token)
                client = ts_module.pro_api()
                client._DataApi__http_url = "https://tx.xiaodefa.top/"
            except Exception as exc:
                raise BackendConnectionError(f"Unable to initialize Tushare client: {exc}") from exc
        else:
            try:
                client = factory(token=token)
            except Exception as exc:
                raise BackendConnectionError(f"Unable to initialize Tushare client: {exc}") from exc
        self._clients[name] = client
        return client

    @staticmethod
    def _catalog(dataset_name: str) -> TushareDatasetCatalog:
        catalog = _TUSHARE_DATASETS.get(dataset_name)
        if catalog is None:
            supported = ", ".join(sorted(_TUSHARE_DATASETS))
            raise DatasetRegistrationError(
                f"Unsupported Tushare dataset {dataset_name!r}; "
                f"supported datasets: {supported}"
            )
        return catalog

    @staticmethod
    def _contract(
        definition: TushareDatasetSpec, catalog: TushareDatasetCatalog
    ) -> DatasetContract:
        semantics = catalog.semantics
        if isinstance(semantics, DisclosureSemantics):
            return DatasetContract(
                table_time_column=semantics.period_column,
                instrument_column=catalog.instrument_column,
                table_identity_columns=semantics.identity_columns,
                table_frequency=semantics.table_frequency,
                panel_time_column=semantics.panel_time_column,
                panel_frequency=semantics.panel_frequency,
                timezone=definition.timezone,
                version=definition.version,
                panel_requires_time_range=True,
            )
        if isinstance(semantics, MembershipSemantics):
            return DatasetContract(
                table_time_column=semantics.table_time_column,
                instrument_column=catalog.instrument_column,
                table_identity_columns=semantics.identity_columns,
                panel_time_column=semantics.panel_time_column,
                panel_frequency=semantics.panel_frequency,
                timezone=definition.timezone,
                version=definition.version,
                table_requires_time_range=True,
                panel_requires_time_range=True,
            )
        return DatasetContract(
            table_time_column=semantics.table_time_column,
            instrument_column=catalog.instrument_column,
            table_identity_columns=semantics.identity_columns,
            table_frequency=semantics.table_frequency,
            timezone=definition.timezone,
            version=definition.version,
            panel_compatible=False,
            table_requires_time_range=True,
        )

    @staticmethod
    def _validate_definition(
        definition: TushareDatasetSpec, catalog: TushareDatasetCatalog
    ) -> None:
        if not isinstance(definition.fixed_params, Mapping):
            raise DatasetRegistrationError("Tushare fixed_params must be a mapping")
        invalid_param_keys = [
            key
            for key in definition.fixed_params
            if not isinstance(key, str) or not key
        ]
        if invalid_param_keys:
            raise DatasetRegistrationError(
                "Tushare fixed_params keys must be non-empty strings"
            )
        schema_names = set(catalog.schema.names)
        semantics = catalog.semantics
        required = {catalog.instrument_column}
        if isinstance(semantics, DisclosureSemantics):
            required.update(
                {
                    semantics.period_column,
                    semantics.disclosure_column,
                    *semantics.identity_columns,
                    *semantics.revision_order,
                    *semantics.table_order,
                }
            )
        elif isinstance(semantics, MembershipSemantics):
            required.update(
                {
                    semantics.table_time_column,
                    semantics.interval_start_column,
                    semantics.interval_end_column,
                    *semantics.identity_columns,
                    *semantics.table_order,
                }
            )
        else:
            required.update(
                {
                    semantics.table_time_column,
                    *semantics.identity_columns,
                    *semantics.table_order,
                }
            )
        missing = required.difference(schema_names)
        if missing:
            raise DatasetRegistrationError(
                f"Tushare dataset {catalog.name!r} is missing configured columns: "
                f"{sorted(missing)}"
            )
        reserved = {"fields"}
        for route in catalog.routes:
            reserved.add(route.instrument_param)
            query_shapes: tuple[object, ...] = (
                route.table_query,
                route.disclosure_query,
            )
            for query_shape in query_shapes:
                if isinstance(query_shape, PeriodQuery):
                    reserved.add(query_shape.period_param)
                elif isinstance(query_shape, DateRangeQuery):
                    reserved.update(
                        {query_shape.start_param, query_shape.end_param}
                    )
                # Membership status is intentionally user-fixable. Without an
                # override the backend queries both current and historical rows.
        conflicts = reserved.intersection(definition.fixed_params)
        if conflicts:
            raise DatasetRegistrationError(
                f"Tushare fixed_params cannot define backend-managed parameters: "
                f"{sorted(conflicts)}"
            )
        if not isinstance(semantics, DisclosureSemantics):
            if definition.disclosure_lag != 0:
                raise DatasetRegistrationError(
                    "disclosure_lag is only valid for disclosure datasets"
                )
            if definition.fetch_buffer_days != 180 or definition.fetch_margin_days != 31:
                raise DatasetRegistrationError(
                    "fetch_buffer_days and fetch_margin_days are only configurable "
                    "for disclosure datasets"
                )

    def _state(
        self, dataset: RegisteredDataset
    ) -> tuple[TushareDatasetSpec, TushareSource, TushareDatasetCatalog]:
        spec = dataset.spec
        source = dataset.source
        if not isinstance(spec, TushareDatasetSpec) or not isinstance(
            source, TushareSource
        ):
            raise SchemaMismatchError("Invalid Tushare registered dataset")
        return spec, source, self._catalog(source.dataset)

    @staticmethod
    def _select_route(
        catalog: TushareDatasetCatalog,
        instruments: tuple[str, ...] | None,
    ) -> TushareApiRoute:
        allowed = (
            {"whole_market", "both"}
            if instruments is None
            else {"instrument_only", "both"}
        )
        for route in catalog.routes:
            if route.universe in allowed:
                return route
        universe = "whole market" if instruments is None else "instrument list"
        raise InvalidQueryError(
            f"Tushare dataset {catalog.name!r} has no route for {universe} queries"
        )

    @staticmethod
    def _unique_columns(columns: tuple[str, ...]) -> tuple[str, ...]:
        result: list[str] = []
        for column in columns:
            if column not in result:
                result.append(column)
        return tuple(result)

    @staticmethod
    def _remote_columns(
        selected: tuple[str, ...],
        catalog: TushareDatasetCatalog,
    ) -> tuple[str, ...]:
        columns = list(selected)
        semantics = catalog.semantics
        if isinstance(semantics, DisclosureSemantics):
            internal = (*semantics.revision_order, *semantics.table_order)
        else:
            internal = semantics.table_order
        for column in internal:
            if column not in columns:
                columns.append(column)
        return tuple(columns)

    def _fetch_table_frames(
        self,
        client: Any,
        fixed_params: Mapping[str, object],
        route: TushareApiRoute,
        query: DataQuery,
        fields: tuple[str, ...],
    ) -> list[pd.DataFrame]:
        """Execute one catalog route without changing logical table semantics."""

        if query.instruments == ():
            return []
        instruments: tuple[str | None, ...] = (
            query.instruments if query.instruments is not None else (None,)
        )
        shape = route.table_query
        periods: tuple[str | None, ...] = (None,)
        statuses: tuple[str | None, ...] = (None,)
        if isinstance(shape, PeriodQuery):
            resolved = self._periods(query.start, query.end)
            if resolved == ():
                return []
            periods = resolved if resolved is not None else (None,)
        elif isinstance(shape, MembershipQuery):
            statuses = (
                (None,)
                if shape.status_param in fixed_params
                else tuple(shape.status_values)
            )

        frames: list[pd.DataFrame] = []
        for instrument in instruments:
            for period in periods:
                for status in statuses:
                    params = self._route_params(
                        fixed_params,
                        route,
                        query,
                        fields,
                        period=period,
                        membership_status=status,
                    )
                    if instrument is not None:
                        params[route.instrument_param] = instrument
                    frames.append(self._call_api(client, route.api_name, params))
        return frames

    def _fetch_disclosure_route_frames(
        self,
        client: Any,
        fixed_params: Mapping[str, object],
        route: TushareApiRoute,
        query: DataQuery,
        fields: tuple[str, ...],
    ) -> list[pd.DataFrame]:
        """Fetch disclosure events through the route chosen for the universe."""

        shape = route.disclosure_query
        if shape is None:
            raise InvalidQueryError(
                f"Tushare api {route.api_name!r} has no disclosure query"
            )
        if query.instruments == ():
            return []
        instruments: tuple[str | None, ...] = (
            query.instruments if query.instruments is not None else (None,)
        )
        frames: list[pd.DataFrame] = []
        for instrument in instruments:
            params = dict(fixed_params)
            params["fields"] = ",".join(fields)
            if query.start is not None:
                params[shape.start_param] = query.start.strftime("%Y%m%d")
            if query.end is not None:
                params[shape.end_param] = query.end.strftime("%Y%m%d")
            if instrument is not None:
                params[route.instrument_param] = instrument
            frames.append(self._call_api(client, route.api_name, params))
        return frames

    @staticmethod
    def _route_params(
        fixed_params: Mapping[str, object],
        route: TushareApiRoute,
        query: DataQuery,
        fields: tuple[str, ...],
        *,
        period: str | None,
        membership_status: str | None,
    ) -> dict[str, object]:
        params = dict(fixed_params)
        params["fields"] = ",".join(fields)
        shape = route.table_query
        if isinstance(shape, PeriodQuery) and period is not None:
            params[shape.period_param] = period
        elif isinstance(shape, DateRangeQuery):
            if query.start is not None:
                params[shape.start_param] = query.start.strftime("%Y%m%d")
            if query.end is not None:
                params[shape.end_param] = query.end.strftime("%Y%m%d")
        elif isinstance(shape, MembershipQuery) and membership_status is not None:
            params[shape.status_param] = membership_status
        return params

    @staticmethod
    def _call_api(client: Any, api_name: str, params: dict[str, object]) -> pd.DataFrame:
        try:
            method = getattr(client, api_name, None)
            if callable(method):
                result = method(**params)
            elif callable(getattr(client, "query", None)):
                result = client.query(api_name, **params)
            else:
                raise AttributeError(f"Tushare client does not expose {api_name!r}")
        except Exception as exc:
            raise RemoteQueryError(f"Tushare query failed for api {api_name!r}: {exc}") from exc
        if not isinstance(result, pd.DataFrame):
            raise RemoteQueryError(
                f"Tushare api {api_name!r} returned {type(result).__name__}, expected DataFrame"
            )
        return result

    def _fetch_calendar(
        self,
        connection: str,
        exchange: str,
        start: datetime,
        end: datetime,
    ) -> list[date]:
        trading: list[date] = []
        year, month = start.year, start.month
        end_year, end_month = end.year, end.month
        while (year, month) <= (end_year, end_month):
            key = (connection, exchange, year, month)
            cached = self._calendar_cache.get(key)
            if cached is None:
                cached = self._fetch_calendar_month(connection, exchange, year, month)
                self._calendar_cache[key] = cached
            trading.extend(cached)
            month += 1
            if month > 12:
                year += 1
                month = 1
        start_date = start.date()
        end_date = end.date()
        return sorted(day for day in trading if start_date <= day <= end_date)

    def _fetch_calendar_month(
        self, connection: str, exchange: str, year: int, month: int
    ) -> list[date]:
        client = self._client(connection)
        first = date(year, month, 1)
        if month == 12:
            last = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last = date(year, month + 1, 1) - timedelta(days=1)
        params: dict[str, object] = {
            "exchange": exchange,
            "start_date": first.strftime("%Y%m%d"),
            "end_date": last.strftime("%Y%m%d"),
            "is_open": "1",
        }
        frame = self._call_api(client, "trade_cal", params)
        if "cal_date" not in frame.columns:
            raise RemoteQueryError(
                "Tushare trade_cal result is missing the 'cal_date' column"
            )
        days = [
            datetime.strptime(str(value), "%Y%m%d").date()
            for value in frame["cal_date"].tolist()
        ]
        days.sort()
        return days

    def _normalize_remote_frames(
        self,
        frames: list[pd.DataFrame],
        catalog: TushareDatasetCatalog,
        columns: tuple[str, ...],
        route: TushareApiRoute,
    ) -> pd.DataFrame:
        normalized: list[pd.DataFrame] = []
        for current in frames:
            if current.empty:
                continue
            missing = set(columns).difference(current.columns)
            if missing:
                raise SchemaMismatchError(
                    f"Tushare api {route.api_name!r} result is missing columns: "
                    f"{sorted(missing)}"
                )
            selected = current.loc[:, list(columns)].copy()
            normalized.append(self._coerce_frame(selected, catalog.schema))
        if normalized:
            return pd.concat(normalized, ignore_index=True)
        empty = pd.DataFrame(columns=columns)
        return self._coerce_frame(empty, catalog.schema)

    @staticmethod
    def _expand_membership_panel(
        frame: pd.DataFrame,
        semantics: MembershipSemantics,
        instrument_column: str,
        query: DataQuery,
        calendar: list[date],
        columns: tuple[str, ...],
    ) -> pd.DataFrame:
        if query.start is None or query.end is None:
            raise InvalidQueryError("Membership panels require both start and end")
        if frame.empty or not calendar:
            return pd.DataFrame(columns=columns)

        panel_start = query.start.date()
        panel_end = query.end.date()
        sessions = [day for day in calendar if panel_start <= day <= panel_end]
        blocks: list[pd.DataFrame] = []
        for _, row in frame.iterrows():
            raw_start = row[semantics.interval_start_column]
            if pd.isna(raw_start):
                continue
            raw_end = row[semantics.interval_end_column]
            interval_start = max(cast(date, raw_start), panel_start)
            interval_end = (
                panel_end
                if pd.isna(raw_end)
                else min(cast(date, raw_end), panel_end)
            )
            active = [day for day in sessions if interval_start <= day <= interval_end]
            if not active:
                continue
            block = pd.DataFrame({semantics.panel_time_column: active})
            for column in frame.columns:
                block[column] = row[column]
            blocks.append(block)
        if not blocks:
            return pd.DataFrame(columns=columns)

        expanded = pd.concat(blocks, ignore_index=True)
        precedence = [
            column
            for column in (semantics.interval_start_column, "is_new")
            if column in expanded.columns
        ]
        sort_columns = [
            semantics.panel_time_column,
            instrument_column,
            *precedence,
        ]
        expanded = expanded.sort_values(
            sort_columns, kind="mergesort", na_position="first"
        )
        keys = [semantics.panel_time_column, instrument_column]
        winners: list[pd.Series] = []
        for _, group in expanded.groupby(keys, sort=False, dropna=False):
            if precedence:
                latest = group.iloc[-1]
                tied = group
                for column in precedence:
                    value = latest[column]
                    tied = tied.loc[
                        tied[column].isna()
                        if pd.isna(value)
                        else tied[column].eq(value)
                    ]
            else:
                tied = group
            comparable = [column for column in columns if column not in keys]
            if len(tied.loc[:, comparable].drop_duplicates()) > 1:
                day, instrument = group.iloc[-1][keys].tolist()
                raise SchemaMismatchError(
                    "Conflicting membership rows have identical precedence for "
                    f"{instrument!r} on {day!r}"
                )
            winners.append(tied.iloc[-1])
        result = pd.DataFrame(winners)
        return result.loc[:, list(columns)].sort_values(keys, kind="mergesort")

    @staticmethod
    def _empty_arrow(schema: pa.Schema, selected: tuple[str, ...]) -> pa.Table:
        return pa.table(
            {
                column: pa.array([], type=schema.field(column).type)
                for column in selected
            }
        )

    @staticmethod
    def _membership_frame_to_arrow(
        frame: pd.DataFrame,
        schema: pa.Schema,
        panel_time_column: str,
        selected: tuple[str, ...],
    ) -> pa.Table:
        fields = [
            pa.field(column, pa.date32())
            if column == panel_time_column
            else schema.field(column)
            for column in selected
        ]
        selected_schema = pa.schema(fields)
        if frame.empty:
            return pa.table(
                {
                    field.name: pa.array([], type=field.type)
                    for field in selected_schema
                }
            )
        try:
            return pa.Table.from_pandas(
                frame.loc[:, list(selected)],
                schema=selected_schema,
                preserve_index=False,
            )
        except (pa.ArrowException, ValueError, TypeError) as exc:
            raise SchemaMismatchError(
                f"Unable to convert Tushare membership panel to Arrow: {exc}"
            ) from exc

    @staticmethod
    def _coerce_frame(frame: pd.DataFrame, schema: pa.Schema) -> pd.DataFrame:
        for field in schema:
            if field.name not in frame.columns:
                continue
            if pa.types.is_date32(field.type):
                frame[field.name] = TushareBackend._coerce_yyyymmdd(
                    frame[field.name], field.name
                )
            elif pa.types.is_string(field.type):
                frame[field.name] = frame[field.name].astype("string")
            elif pa.types.is_integer(field.type):
                frame[field.name] = pd.to_numeric(frame[field.name], errors="coerce").astype(
                    "Int64"
                )
            elif pa.types.is_floating(field.type):
                frame[field.name] = pd.to_numeric(frame[field.name], errors="coerce")
        return frame

    @staticmethod
    def _coerce_yyyymmdd(series: pd.Series, name: str) -> pd.Series:
        result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
        mask = series.notna() & (series.astype("string") != "")
        if mask.any():
            parsed = pd.to_datetime(
                series.loc[mask].astype("string"), format="%Y%m%d", errors="coerce"
            )
            if parsed.isna().any():
                bad = series.loc[mask][parsed.isna()].head(5).to_list()
                raise SchemaMismatchError(
                    f"Tushare column {name!r} contains invalid YYYYMMDD values: {bad}"
                )
            result.loc[mask] = parsed
        return result.dt.date

    @staticmethod
    def _filter_time(
        frame: pd.DataFrame,
        time_column: str,
        query: DataQuery,
    ) -> pd.DataFrame:
        if frame.empty:
            return frame
        values = pd.to_datetime(frame[time_column])
        if query.start is not None:
            start = pd.Timestamp(query.start.date())
            frame = frame.loc[values.notna() & (values >= start)]
            values = values.loc[frame.index]
        if query.end is not None:
            end = pd.Timestamp(query.end.date())
            frame = frame.loc[values.notna() & (values <= end)]
        return frame

    @staticmethod
    def _filter_membership_overlap(
        frame: pd.DataFrame,
        semantics: MembershipSemantics,
        query: DataQuery,
    ) -> pd.DataFrame:
        """Keep intervals that overlap the closed query range."""

        if frame.empty:
            return frame
        if query.start is not None:
            start = pd.Timestamp(query.start.date())
            interval_ends = pd.to_datetime(
                frame[semantics.interval_end_column]
            )
            frame = frame.loc[
                interval_ends.isna() | (interval_ends >= start)
            ]
        if query.end is not None:
            end = pd.Timestamp(query.end.date())
            interval_starts = pd.to_datetime(
                frame[semantics.interval_start_column]
            )
            frame = frame.loc[
                interval_starts.notna() & (interval_starts <= end)
            ]
        return frame

    @staticmethod
    def _sort_by(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
        if frame.empty:
            return frame
        available = [column for column in columns if column in frame.columns]
        if not available:
            return frame
        return frame.sort_values(
            available, kind="mergesort", na_position="last"
        )

    @staticmethod
    def _frame_to_arrow(
        frame: pd.DataFrame,
        schema: pa.Schema,
        selected: tuple[str, ...],
    ) -> pa.Table:
        selected_schema = pa.schema([schema.field(column) for column in selected])
        if frame.empty:
            return pa.table(
                {
                    field.name: pa.array([], type=field.type)
                    for field in selected_schema
                }
            )
        try:
            return pa.Table.from_pandas(
                frame.loc[:, list(selected)],
                schema=selected_schema,
                preserve_index=False,
            )
        except (pa.ArrowException, ValueError, TypeError) as exc:
            raise SchemaMismatchError(
                f"Unable to convert Tushare result to Arrow: {exc}"
            ) from exc

    @staticmethod
    def _periods(start: datetime | None, end: datetime | None) -> tuple[str, ...] | None:
        if start is None or end is None:
            return None
        start_date = start.date()
        end_date = end.date()
        periods: list[str] = []
        for year in range(start_date.year, end_date.year + 1):
            for month, day in _QUARTER_ENDS:
                current = date(year, month, day)
                if start_date <= current <= end_date:
                    periods.append(current.strftime("%Y%m%d"))
        return tuple(periods)

    @staticmethod
    def _close_client(client: Any) -> None:
        close = getattr(client, "close", None)
        if callable(close):
            close()
