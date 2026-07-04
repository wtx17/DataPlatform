"""Tushare backend implemented with the Tushare Pro API."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, replace
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
    DatasetDefinition,
    RegisteredDataset,
    TushareConfig,
    TushareDatasetSpec,
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
    "date",
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
_INDUSTRY_MEMBER_DATE_FIELDS = frozenset({"date", "in_date", "out_date"})


@dataclass(frozen=True, slots=True)
class TushareTableCatalog:
    api_name: str
    schema: pa.Schema
    query_style: str
    period_param: str | None
    start_param: str | None
    end_param: str | None
    instrument_param: str
    dedupe_keys: tuple[str, ...]
    dedupe_sort: tuple[str, ...]
    order_columns: tuple[str, ...]
    requires_instrument: bool = False
    default_time_column: str | None = None
    default_frequency: str | None = None
    requires_time_range: bool = False
    panel_compatible: bool | None = None
    disclosure_column: str = "f_ann_date"
    period_column: str = "end_date"
    disclosure_start_param: str | None = None
    disclosure_end_param: str | None = None
    interval_start_column: str | None = None
    interval_end_column: str | None = None


@dataclass(frozen=True, slots=True)
class TushareSource:
    connection: str
    api_name: str
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
_TUSHARE_TABLES = {
    "income": TushareTableCatalog(
        api_name="income",
        schema=_INCOME_SCHEMA,
        query_style="period_range",
        period_param="period",
        start_param="start_date",
        end_param="end_date",
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("f_ann_date", "ann_date", "update_flag"),
        order_columns=("end_date", "ts_code"),
        requires_instrument=True,
        disclosure_start_param="start_date",
        disclosure_end_param="end_date",
    ),
    "income_vip": TushareTableCatalog(
        api_name="income_vip",
        schema=_INCOME_SCHEMA,
        query_style="period_range",
        period_param="period",
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("f_ann_date", "ann_date", "update_flag"),
        order_columns=("end_date", "ts_code"),
        disclosure_start_param="start_date",
        disclosure_end_param="end_date",
    ),
    "balancesheet": TushareTableCatalog(
        api_name="balancesheet",
        schema=_BALANCESHEET_SCHEMA,
        query_style="period_range",
        period_param="period",
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("f_ann_date", "ann_date", "update_flag"),
        order_columns=("end_date", "ts_code"),
        requires_instrument=True,
        disclosure_start_param="start_date",
        disclosure_end_param="end_date",
    ),
    "balancesheet_vip": TushareTableCatalog(
        api_name="balancesheet_vip",
        schema=_BALANCESHEET_SCHEMA,
        query_style="period_range",
        period_param="period",
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("f_ann_date", "ann_date", "update_flag"),
        order_columns=("end_date", "ts_code"),
        disclosure_start_param="start_date",
        disclosure_end_param="end_date",
    ),
    "cashflow": TushareTableCatalog(
        api_name="cashflow",
        schema=_CASHFLOW_SCHEMA,
        query_style="period_range",
        period_param="period",
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("f_ann_date", "ann_date", "update_flag"),
        order_columns=("end_date", "ts_code"),
        requires_instrument=True,
        disclosure_start_param="start_date",
        disclosure_end_param="end_date",
    ),
    "cashflow_vip": TushareTableCatalog(
        api_name="cashflow_vip",
        schema=_CASHFLOW_SCHEMA,
        query_style="period_range",
        period_param="period",
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("f_ann_date", "ann_date", "update_flag"),
        order_columns=("end_date", "ts_code"),
        disclosure_start_param="start_date",
        disclosure_end_param="end_date",
    ),
    "fina_indicator": TushareTableCatalog(
        api_name="fina_indicator",
        schema=_FINA_INDICATOR_SCHEMA,
        query_style="period_range",
        period_param="period",
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("ann_date", "update_flag"),
        order_columns=("end_date", "ts_code"),
        requires_instrument=True,
        disclosure_column="ann_date",
        disclosure_start_param="start_date",
        disclosure_end_param="end_date",
    ),
    "fina_indicator_vip": TushareTableCatalog(
        api_name="fina_indicator_vip",
        schema=_FINA_INDICATOR_SCHEMA,
        query_style="period_range",
        period_param="period",
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("ann_date", "update_flag"),
        order_columns=("end_date", "ts_code"),
        disclosure_column="ann_date",
        disclosure_start_param="start_date",
        disclosure_end_param="end_date",
    ),
    "express": TushareTableCatalog(
        api_name="express",
        schema=_EXPRESS_SCHEMA,
        query_style="period_range",
        period_param="period",
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("ann_date",),
        order_columns=("end_date", "ts_code"),
        requires_instrument=True,
        disclosure_column="ann_date",
        disclosure_start_param="start_date",
        disclosure_end_param="end_date",
    ),
    "express_vip": TushareTableCatalog(
        api_name="express_vip",
        schema=_EXPRESS_SCHEMA,
        query_style="period_range",
        period_param="period",
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("ann_date",),
        order_columns=("end_date", "ts_code"),
        disclosure_column="ann_date",
        disclosure_start_param="start_date",
        disclosure_end_param="end_date",
    ),
    "forecast": TushareTableCatalog(
        api_name="forecast",
        schema=_FORECAST_SCHEMA,
        query_style="period_range",
        period_param="period",
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("ann_date", "first_ann_date"),
        order_columns=("end_date", "ts_code"),
        requires_instrument=True,
        disclosure_column="ann_date",
        disclosure_start_param="start_date",
        disclosure_end_param="end_date",
    ),
    "forecast_vip": TushareTableCatalog(
        api_name="forecast_vip",
        schema=_FORECAST_SCHEMA,
        query_style="period_range",
        period_param="period",
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("ann_date", "first_ann_date"),
        order_columns=("end_date", "ts_code"),
        disclosure_column="ann_date",
        disclosure_start_param="start_date",
        disclosure_end_param="end_date",
    ),
    "stk_holdernumber": TushareTableCatalog(
        api_name="stk_holdernumber",
        schema=_STK_HOLDERNUMBER_SCHEMA,
        query_style="date_range",
        period_param=None,
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("ann_date",),
        order_columns=("end_date", "ts_code"),
        disclosure_column="ann_date",
        disclosure_start_param="start_date",
        disclosure_end_param="end_date",
    ),
    "stk_holdertrade": TushareTableCatalog(
        api_name="stk_holdertrade",
        schema=_STK_HOLDERTRADE_SCHEMA,
        query_style="date_range",
        period_param=None,
        start_param="start_date",
        end_param="end_date",
        instrument_param="ts_code",
        dedupe_keys=(),
        dedupe_sort=(),
        order_columns=("ann_date", "ts_code", "holder_name"),
        default_time_column="ann_date",
        default_frequency="d",
        requires_time_range=True,
        panel_compatible=False,
    ),
    "ci_index_member": TushareTableCatalog(
        api_name="ci_index_member",
        schema=_INDUSTRY_MEMBER_SCHEMA,
        query_style="membership_interval",
        period_param=None,
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("date", "ts_code"),
        dedupe_sort=("in_date", "is_new"),
        order_columns=("date", "ts_code"),
        default_time_column="date",
        default_frequency="d",
        requires_time_range=True,
        interval_start_column="in_date",
        interval_end_column="out_date",
    ),
    "index_member_all": TushareTableCatalog(
        api_name="index_member_all",
        schema=_INDUSTRY_MEMBER_SCHEMA,
        query_style="membership_interval",
        period_param=None,
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("date", "ts_code"),
        dedupe_sort=("in_date", "is_new"),
        order_columns=("date", "ts_code"),
        default_time_column="date",
        default_frequency="d",
        requires_time_range=True,
        interval_start_column="in_date",
        interval_end_column="out_date",
    ),
}


class TushareBackend:
    def __init__(self, client_factory: Callable[..., Any] | None = None) -> None:
        self._configs: dict[str, TushareConfig] = {}
        self._clients: dict[str, Any] = {}
        self._client_factory = client_factory
        self._calendar_cache: dict[tuple[str, str, int, int], list[date]] = {}

    def add_connection(self, name: str, config: TushareConfig) -> None:
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
        if not isinstance(definition, TushareDatasetSpec):
            raise DatasetRegistrationError("Tushare backend requires TushareDatasetSpec")
        catalog = self._catalog(definition.api_name)
        definition = self._normalize_definition(definition, catalog)
        self._validate_definition(definition, catalog)
        self._client(definition.connection)
        normalized = json.dumps(
            [(field.name, str(field.type)) for field in catalog.schema],
            separators=(",", ":"),
        )
        source = TushareSource(
            definition.connection,
            catalog.api_name,
            hashlib.sha256(normalized.encode()).hexdigest(),
            dict(definition.fixed_params),
        )
        return RegisteredDataset(definition, catalog.schema, source)

    def scan(self, dataset: RegisteredDataset, query: DataQuery) -> pa.Table:
        spec = dataset.spec
        source = dataset.source
        if not isinstance(spec, TushareDatasetSpec) or not isinstance(source, TushareSource):
            raise SchemaMismatchError("Invalid Tushare registered dataset")
        catalog = self._catalog(source.api_name)
        client = self._client(source.connection)
        selected = self._selected_columns(spec, query.fields)
        if catalog.query_style == "membership_interval":
            remote_fields = self._remote_columns(selected, spec, catalog)
            frames = self._fetch_membership_frames(
                client, spec, catalog, query, remote_fields
            )
            frame = self._normalize_membership_frames(
                frames, spec, catalog, query, remote_fields, source.connection
            )
            frame = self._project_frame(frame, spec, catalog, query, selected)
            return self._to_arrow(frame, catalog.schema, selected)
        remote_fields = self._remote_columns(selected, spec, catalog)
        frames = self._fetch_frames(client, spec, catalog, query, remote_fields)
        frame = self._normalize_frames(frames, spec, catalog, query, remote_fields)
        frame = self._project_frame(frame, spec, catalog, query, selected)
        return self._to_arrow(frame, catalog.schema, selected)

    def scan_disclosure_events(
        self, dataset: RegisteredDataset, query: DataQuery
    ) -> pa.Table:
        spec = dataset.spec
        source = dataset.source
        if not isinstance(spec, TushareDatasetSpec) or not isinstance(source, TushareSource):
            raise SchemaMismatchError("Invalid Tushare registered dataset")
        if query.start is None or query.end is None:
            raise InvalidQueryError(
                f"Dataset {spec.name!r} pit_daily panel requires both start and end"
            )
        catalog = self._catalog(source.api_name)
        if (
            catalog.disclosure_start_param is None
            or catalog.disclosure_end_param is None
        ):
            raise InvalidQueryError(
                f"Tushare api {catalog.api_name!r} cannot serve a pit_daily panel"
            )
        if catalog.requires_instrument and query.instruments is None:
            raise InvalidQueryError(
                f"Tushare api {catalog.api_name!r} pit_daily panel requires "
                f"instruments; use {catalog.api_name}_vip for whole-market panels"
            )
        client = self._client(source.connection)
        selected = self._disclosure_columns(spec, catalog, query.fields)
        remote_fields = self._remote_columns(selected, spec, catalog)
        fetch_start = query.start - timedelta(days=spec.fetch_buffer_days)
        fetch_query = DataQuery(
            query.fields,
            fetch_start,
            query.end,
            query.instruments,
            None,
        )
        frames = self._fetch_disclosure_frames(
            client, spec, catalog, fetch_query, remote_fields
        )
        frame = self._normalize_frames(
            frames,
            spec,
            catalog,
            fetch_query,
            remote_fields,
            time_column=catalog.disclosure_column,
            dedupe=False,
        )
        frame = self._dedupe_disclosure_events(frame, catalog)
        frame = self._sort_disclosure_events(frame, catalog)
        return self._to_arrow(frame, catalog.schema, selected)

    def trade_calendar(self, dataset: RegisteredDataset, query: DataQuery) -> list[date]:
        spec = dataset.spec
        source = dataset.source
        if not isinstance(spec, TushareDatasetSpec) or not isinstance(source, TushareSource):
            raise SchemaMismatchError("Invalid Tushare registered dataset")
        if query.start is None or query.end is None:
            raise InvalidQueryError(
                f"Dataset {spec.name!r} pit_daily panel requires both start and end"
            )
        start = query.start - timedelta(days=spec.fetch_buffer_days)
        end = query.end + timedelta(days=spec.fetch_margin_days)
        return self._fetch_calendar(source.connection, spec.calendar_exchange, start, end)

    def pit_panel_columns(self, dataset: RegisteredDataset) -> tuple[str, str]:
        spec = dataset.spec
        source = dataset.source
        if not isinstance(spec, TushareDatasetSpec) or not isinstance(source, TushareSource):
            raise SchemaMismatchError("Invalid Tushare registered dataset")
        catalog = self._catalog(source.api_name)
        return catalog.disclosure_column, catalog.period_column

    def fingerprint(self, dataset: RegisteredDataset) -> dict[str, object]:
        spec = dataset.spec
        source = dataset.source
        if not isinstance(spec, TushareDatasetSpec) or not isinstance(source, TushareSource):
            raise SchemaMismatchError("Invalid Tushare registered dataset")
        return {
            "backend": "tushare",
            "connection": source.connection,
            "api_name": source.api_name,
            "schema_hash": source.schema_hash,
            "fixed_params": {str(key): str(value) for key, value in source.fixed_params.items()},
        }

    def close(self) -> None:
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
    def _catalog(api_name: str) -> TushareTableCatalog:
        catalog = _TUSHARE_TABLES.get(api_name)
        if catalog is None:
            supported = ", ".join(sorted(_TUSHARE_TABLES))
            raise DatasetRegistrationError(
                f"Unsupported Tushare api {api_name!r}; supported APIs: {supported}"
            )
        return catalog

    @staticmethod
    def _normalize_definition(
        definition: TushareDatasetSpec, catalog: TushareTableCatalog
    ) -> TushareDatasetSpec:
        normalized = definition
        if (
            catalog.default_time_column is not None
            and normalized.time_column == "end_date"
        ):
            normalized = replace(normalized, time_column=catalog.default_time_column)
        if catalog.default_frequency is not None and normalized.frequency is None:
            normalized = replace(normalized, frequency=catalog.default_frequency)
        if catalog.requires_time_range and normalized.require_time_range is not True:
            normalized = replace(normalized, require_time_range=True)
        if catalog.panel_compatible is not None:
            normalized = replace(normalized, panel_compatible=catalog.panel_compatible)
        return normalized

    @staticmethod
    def _validate_definition(
        definition: TushareDatasetSpec, catalog: TushareTableCatalog
    ) -> None:
        schema_names = set(catalog.schema.names)
        required = {definition.time_column, definition.instrument_column}
        required.update(catalog.dedupe_keys)
        required.update(catalog.dedupe_sort)
        required.update(definition.order_columns)
        missing = required.difference(schema_names)
        if missing:
            raise DatasetRegistrationError(
                f"Tushare api {definition.api_name!r} is missing configured columns: "
                f"{sorted(missing)}"
            )
        reserved = {"fields"}
        if catalog.period_param:
            reserved.add(catalog.period_param)
        if catalog.start_param:
            reserved.add(catalog.start_param)
        if catalog.end_param:
            reserved.add(catalog.end_param)
        reserved.add(catalog.instrument_param)
        conflicts = reserved.intersection(definition.fixed_params)
        if conflicts:
            raise DatasetRegistrationError(
                f"Tushare fixed_params cannot define backend-managed parameters: "
                f"{sorted(conflicts)}"
            )
        if TushareBackend._is_pit_definition(definition):
            disclosure_reserved = {catalog.instrument_param, "fields"}
            if catalog.disclosure_start_param is not None:
                disclosure_reserved.add(catalog.disclosure_start_param)
            if catalog.disclosure_end_param is not None:
                disclosure_reserved.add(catalog.disclosure_end_param)
            disclosure_conflicts = disclosure_reserved.intersection(
                definition.fixed_params
            )
            if disclosure_conflicts:
                raise DatasetRegistrationError(
                    "Tushare fixed_params cannot define pit_daily-managed parameters: "
                    f"{sorted(disclosure_conflicts)}"
                )

    @staticmethod
    def _is_pit_definition(definition: TushareDatasetSpec) -> bool:
        return definition.panel_mode == "pit_daily" or definition.point_in_time

    @staticmethod
    def _selected_columns(spec: TushareDatasetSpec, fields: tuple[str, ...]) -> tuple[str, ...]:
        columns: list[str] = []
        for column in (spec.time_column, spec.instrument_column, *fields):
            if column not in columns:
                columns.append(column)
        return tuple(columns)

    @staticmethod
    def _disclosure_columns(
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        fields: tuple[str, ...],
    ) -> tuple[str, ...]:
        columns: list[str] = []
        for column in (
            catalog.disclosure_column,
            spec.instrument_column,
            catalog.period_column,
            *fields,
        ):
            if column not in columns:
                columns.append(column)
        return tuple(columns)

    @staticmethod
    def _remote_columns(
        selected: tuple[str, ...],
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
    ) -> tuple[str, ...]:
        if catalog.query_style == "membership_interval":
            columns = [
                column for column in selected if column != spec.time_column
            ]
            for column in (
                catalog.interval_start_column,
                catalog.interval_end_column,
                *catalog.dedupe_sort,
                *spec.order_columns,
            ):
                if (
                    column is not None
                    and column != spec.time_column
                    and column not in columns
                ):
                    columns.append(column)
            return tuple(columns)
        columns = list(selected)
        for column in (*catalog.dedupe_keys, *catalog.dedupe_sort, *spec.order_columns):
            if column not in columns:
                columns.append(column)
        return tuple(columns)

    def _fetch_frames(
        self,
        client: Any,
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        query: DataQuery,
        fields: tuple[str, ...],
    ) -> list[pd.DataFrame]:
        periods = (
            self._periods(query.start, query.end)
            if catalog.query_style == "period_range"
            else None
        )
        if periods == ():
            return []
        instruments = query.instruments
        if catalog.requires_instrument and instruments is None:
            raise InvalidQueryError(
                f"Tushare api {catalog.api_name!r} requires instruments; use "
                f"{catalog.api_name}_vip for whole-market period queries"
            )
        if instruments == ():
            return []
        period_values: tuple[str | None, ...] = periods if periods is not None else (None,)
        instrument_values: tuple[str | None, ...]
        instrument_values = instruments if instruments is not None else (None,)
        frames: list[pd.DataFrame] = []
        for period in period_values:
            for instrument in instrument_values:
                params = self._call_params(spec, catalog, query, fields, period, instrument)
                frames.append(self._call_api(client, catalog.api_name, params))
        return frames

    def _fetch_disclosure_frames(
        self,
        client: Any,
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        query: DataQuery,
        fields: tuple[str, ...],
    ) -> list[pd.DataFrame]:
        instruments = query.instruments
        if instruments == ():
            return []
        if instruments is None and catalog.requires_instrument:
            raise InvalidQueryError(
                f"Tushare api {catalog.api_name!r} pit_daily query requires instruments"
            )
        instrument_values = instruments if instruments is not None else (None,)
        frames: list[pd.DataFrame] = []
        for instrument in instrument_values:
            params = self._disclosure_call_params(spec, catalog, query, fields, instrument)
            frames.append(self._call_api(client, catalog.api_name, params))
        return frames

    def _fetch_membership_frames(
        self,
        client: Any,
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        query: DataQuery,
        fields: tuple[str, ...],
    ) -> list[pd.DataFrame]:
        instruments = query.instruments
        if instruments == ():
            return []
        instrument_values = instruments if instruments is not None else (None,)
        is_new_values: tuple[str | None, ...]
        is_new_values = (None,) if "is_new" in spec.fixed_params else ("Y", "N")
        frames: list[pd.DataFrame] = []
        for instrument in instrument_values:
            for is_new in is_new_values:
                params = self._membership_call_params(
                    spec, catalog, fields, instrument, is_new
                )
                frames.append(self._call_api(client, catalog.api_name, params))
        return frames

    @staticmethod
    def _call_params(
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        query: DataQuery,
        fields: tuple[str, ...],
        period: str | None,
        instrument: str | None,
    ) -> dict[str, object]:
        params = dict(spec.fixed_params)
        params["fields"] = ",".join(fields)
        if catalog.query_style == "period_range":
            if period is not None and catalog.period_param is not None:
                params[catalog.period_param] = period
        else:
            if query.start is not None and catalog.start_param is not None:
                params[catalog.start_param] = query.start.strftime("%Y%m%d")
            if query.end is not None and catalog.end_param is not None:
                params[catalog.end_param] = query.end.strftime("%Y%m%d")
        if instrument is not None:
            params[catalog.instrument_param] = instrument
        return params

    @staticmethod
    def _membership_call_params(
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        fields: tuple[str, ...],
        instrument: str | None,
        is_new: str | None,
    ) -> dict[str, object]:
        params = dict(spec.fixed_params)
        params["fields"] = ",".join(fields)
        if instrument is not None:
            params[catalog.instrument_param] = instrument
        if is_new is not None:
            params["is_new"] = is_new
        return params

    @staticmethod
    def _disclosure_call_params(
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        query: DataQuery,
        fields: tuple[str, ...],
        instrument: str | None,
    ) -> dict[str, object]:
        params = dict(spec.fixed_params)
        params["fields"] = ",".join(fields)
        if query.start is not None and catalog.disclosure_start_param is not None:
            params[catalog.disclosure_start_param] = query.start.strftime("%Y%m%d")
        if query.end is not None and catalog.disclosure_end_param is not None:
            params[catalog.disclosure_end_param] = query.end.strftime("%Y%m%d")
        if instrument is not None:
            params[catalog.instrument_param] = instrument
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

    def _normalize_membership_frames(
        self,
        frames: list[pd.DataFrame],
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        query: DataQuery,
        columns: tuple[str, ...],
        connection: str,
    ) -> pd.DataFrame:
        if query.start is None or query.end is None:
            raise InvalidQueryError(
                f"Dataset {spec.name!r} requires both start and end for membership panels"
            )
        normalized_frames: list[pd.DataFrame] = []
        for current in frames:
            if current.empty:
                continue
            missing = set(columns).difference(current.columns)
            if missing:
                raise SchemaMismatchError(
                    f"Tushare api {catalog.api_name!r} result is missing columns: "
                    f"{sorted(missing)}"
                )
            current = current.loc[:, list(columns)].copy()
            normalized_frames.append(self._coerce_frame(current, catalog.schema))
        base_columns = self._membership_columns(spec, columns)
        if normalized_frames:
            frame = pd.concat(normalized_frames, ignore_index=True)
        else:
            frame = pd.DataFrame(columns=columns)
            frame = self._coerce_frame(frame, catalog.schema)
        calendar = self._fetch_calendar(
            connection,
            spec.calendar_exchange,
            query.start,
            query.end,
        )
        expanded = self._expand_membership_intervals(
            frame, spec, catalog, query, calendar, base_columns
        )
        return self._sort_frame(expanded, spec, catalog)

    @staticmethod
    def _membership_columns(
        spec: TushareDatasetSpec, columns: tuple[str, ...]
    ) -> tuple[str, ...]:
        result = [spec.time_column]
        for column in columns:
            if column not in result:
                result.append(column)
        return tuple(result)

    @staticmethod
    def _expand_membership_intervals(
        frame: pd.DataFrame,
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        query: DataQuery,
        calendar: list[date],
        columns: tuple[str, ...],
    ) -> pd.DataFrame:
        start_column = catalog.interval_start_column
        end_column = catalog.interval_end_column
        if start_column is None or end_column is None:
            raise SchemaMismatchError(
                f"Tushare api {catalog.api_name!r} is missing interval columns"
            )
        if query.start is None or query.end is None:
            raise InvalidQueryError(
                f"Dataset {spec.name!r} requires both start and end for membership panels"
            )
        if frame.empty:
            return pd.DataFrame(columns=columns)
        query_start = query.start.date()
        query_end = query.end.date()
        calendar_days = [day for day in calendar if query_start <= day <= query_end]
        if not calendar_days:
            return pd.DataFrame(columns=columns)

        blocks: list[pd.DataFrame] = []
        for _, row in frame.iterrows():
            in_date = row[start_column]
            if pd.isna(in_date):
                continue
            out_date = row[end_column]
            interval_start = max(cast(date, in_date), query_start)
            interval_end = query_end if pd.isna(out_date) else min(cast(date, out_date), query_end)
            if interval_start > interval_end:
                continue
            active_days = [
                current for current in calendar_days if interval_start <= current <= interval_end
            ]
            if not active_days:
                continue
            block = pd.DataFrame({spec.time_column: active_days})
            for column in frame.columns:
                if column != spec.time_column:
                    block[column] = row[column]
            blocks.append(block)
        if not blocks:
            return pd.DataFrame(columns=columns)
        expanded = pd.concat(blocks, ignore_index=True)
        sort_columns = [
            column
            for column in (
                spec.time_column,
                spec.instrument_column,
                start_column,
                "is_new",
            )
            if column in expanded.columns
        ]
        if sort_columns:
            expanded = expanded.sort_values(
                sort_columns, kind="mergesort", na_position="last"
            )
        expanded = expanded.drop_duplicates(
            [spec.time_column, spec.instrument_column], keep="last"
        )
        return expanded.loc[:, list(columns)]

    def _normalize_frames(
        self,
        frames: list[pd.DataFrame],
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        query: DataQuery,
        columns: tuple[str, ...],
        *,
        time_column: str | None = None,
        dedupe: bool = True,
    ) -> pd.DataFrame:
        normalized_frames: list[pd.DataFrame] = []
        for current in frames:
            if current.empty:
                continue
            missing = set(columns).difference(current.columns)
            if missing:
                raise SchemaMismatchError(
                    f"Tushare api {catalog.api_name!r} result is missing columns: "
                    f"{sorted(missing)}"
                )
            current = current.loc[:, list(columns)].copy()
            normalized_frames.append(self._coerce_frame(current, catalog.schema))
        if normalized_frames:
            frame = pd.concat(normalized_frames, ignore_index=True)
        else:
            frame = pd.DataFrame(columns=columns)
            frame = self._coerce_frame(frame, catalog.schema)
        frame = self._filter_time(frame, time_column or spec.time_column, query)
        if dedupe:
            frame = self._dedupe(frame, catalog)
        return self._sort_frame(frame, spec, catalog)

    @staticmethod
    def _project_frame(
        frame: pd.DataFrame,
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        query: DataQuery,
        selected: tuple[str, ...],
    ) -> pd.DataFrame:
        if query.limit is not None:
            frame = frame.head(query.limit)
        missing = set(selected).difference(frame.columns)
        if missing:
            raise SchemaMismatchError(
                f"Tushare api {catalog.api_name!r} normalized result is missing columns: "
                f"{sorted(missing)}"
            )
        return frame.loc[:, list(selected)]

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
        if query.start is not None:
            frame = frame.loc[
                frame[time_column].notna() & (frame[time_column] >= query.start.date())
            ]
        if query.end is not None:
            frame = frame.loc[
                frame[time_column].notna() & (frame[time_column] <= query.end.date())
            ]
        return frame

    @staticmethod
    def _dedupe(frame: pd.DataFrame, catalog: TushareTableCatalog) -> pd.DataFrame:
        if frame.empty or not catalog.dedupe_keys:
            return frame
        sort_columns = [column for column in catalog.dedupe_sort if column in frame.columns]
        if sort_columns:
            frame = frame.sort_values(
                sort_columns,
                ascending=[False] * len(sort_columns),
                kind="mergesort",
                na_position="last",
            )
        return frame.drop_duplicates(list(catalog.dedupe_keys), keep="first")

    @staticmethod
    def _dedupe_disclosure_events(
        frame: pd.DataFrame, catalog: TushareTableCatalog
    ) -> pd.DataFrame:
        if frame.empty:
            return frame
        subset = [
            column
            for column in (
                catalog.instrument_param,
                catalog.period_column,
                catalog.disclosure_column,
            )
            if column in frame.columns
        ]
        if len(subset) < 3:
            return frame
        sort_columns = [column for column in catalog.dedupe_sort if column in frame.columns]
        if sort_columns:
            frame = frame.sort_values(
                sort_columns,
                ascending=[False] * len(sort_columns),
                kind="mergesort",
                na_position="last",
            )
        return frame.drop_duplicates(subset, keep="first")

    @staticmethod
    def _sort_disclosure_events(
        frame: pd.DataFrame, catalog: TushareTableCatalog
    ) -> pd.DataFrame:
        if frame.empty:
            return frame
        columns = [
            column
            for column in (
                catalog.disclosure_column,
                catalog.instrument_param,
                catalog.period_column,
            )
            if column in frame.columns
        ]
        if not columns:
            return frame
        return frame.sort_values(columns, kind="mergesort", na_position="last")

    @staticmethod
    def _sort_frame(
        frame: pd.DataFrame,
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
    ) -> pd.DataFrame:
        if frame.empty:
            return frame
        order_columns = spec.order_columns or catalog.order_columns
        available = [column for column in order_columns if column in frame.columns]
        if not available:
            return frame
        return frame.sort_values(available, kind="mergesort", na_position="last")

    @staticmethod
    def _to_arrow(
        frame: pd.DataFrame,
        schema: pa.Schema,
        selected: tuple[str, ...],
    ) -> pa.Table:
        selected_schema = pa.schema([schema.field(column) for column in selected])
        if frame.empty:
            return pa.table(
                {field.name: pa.array([], type=field.type) for field in selected_schema}
            )
        try:
            return pa.Table.from_pandas(frame, schema=selected_schema, preserve_index=False)
        except (pa.ArrowException, ValueError, TypeError) as exc:
            raise SchemaMismatchError(f"Unable to convert Tushare result to Arrow: {exc}") from exc

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
