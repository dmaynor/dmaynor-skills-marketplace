"""Regression tests for SAT2 contract branches and malformed data."""
import copy
import unittest
from validate_output import validate

def analysis():
    return {'schema':'sat2.output.v1','claim':'cause','mode':'CRASH_ANALYSIS','result_kind':'analysis','gate':{'passed':True,'note':'competing causes','conditions':['competition']},'hypotheses':[{'id':f'H{i}','text':'candidate','category':cat,'prior':0,'prior_basis':'subjective prior','falsified_by':'measurement'} for i,cat in enumerate(['obvious','null','uncomfortable','systemic','malicious'])],'discriminating_tests':[{'id':'T1','action':'measure','discriminates':['H0','H1'],'order':1,'exit_condition':'measurement separates causes'}],'completion':{'condition':'unresolved','discriminated':False,'remaining_tests':['T1'],'statement':'pending measurement'},'assessment':{'conclusion':'unresolved','confidence_term':'Moderate','confidence_range':[.5,.6],'basis':'subjective prior'},'assumptions':['logs accurate'],'limitations':['measurement pending'],'ach':{'included':False,'reason':'not requested'}}

class ContractTests(unittest.TestCase):
    def test_analysis_zero_prior(self):
        validate(analysis())
    def test_completion_branches(self):
        for cond in ('a','b','c'):
            d=analysis();d['completion']['condition']=cond
            if cond=='a': d['completion'].update(discriminated=True,remaining_tests=[])
            if cond=='b': d['discriminating_tests'][0].update(owner='operator',queue_evidence='job-123 accepted')
            if cond=='c': d['completion']['budget_exhaustion_source']='caller: budget exhausted'
            validate(d)
    def test_direct(self):
        validate({'schema':'sat2.output.v1','claim':'equal hashes','mode':'STATEMENT_ANALYSIS','result_kind':'direct','gate':{'passed':False,'note':'hash compared'},'direct_result':{'result':'equal','source':'comparison output'},'completion':{'condition':'direct','discriminated':True,'remaining_tests':[],'statement':'resolved'}})
    def test_error(self):
        validate({'schema':'sat2.output.v1','error':{'code':'bad_input','message':'missing claim'}})
    def test_invalid_variants(self):
        mutations=[lambda d:d.update(schema='wrong'),lambda d:d.update(gate=[]),lambda d:d.update(hypotheses=[None]*5),lambda d:d.update(discriminating_tests=[]),lambda d:d['hypotheses'][0].update(prior=True),lambda d:d['assessment'].update(confidence_range=[.9,.2]),lambda d:d['completion'].update(condition='a'),lambda d:d['completion'].update(condition='b'),lambda d:d['completion'].update(condition='c'),lambda d:d['completion'].update(remaining_tests=['unknown']),lambda d:d['discriminating_tests'][0].update(order=2),lambda d:d['discriminating_tests'][0].update(discriminates=['H0','H0']),lambda d:d['ach'].update(included=True)]
        for mutate in mutations:
            d=copy.deepcopy(analysis());mutate(d)
            with self.subTest(doc=d), self.assertRaises(ValueError): validate(d)
    def test_error_schema_required(self):
        with self.assertRaises(ValueError): validate({'error':{'code':'bad_input','message':'bad'}})

if __name__=='__main__': unittest.main()
