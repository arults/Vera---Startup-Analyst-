import random
import unittest
from aj_explicit_history import History, Transition, State, validate
from first_success import InitialPostPolicy
from lost_followup_sensitivity import (
    Endpoint, Direction, FollowupKind, PreparedFollowup, build_scenario)


class SensitivityTests(unittest.TestCase):
    def record(self, *, name="a", state=State.PRE, end=2, cap=10,
               kind=FollowupKind.LOST, transitions=(), company="co"):
        return PreparedFollowup(History(name, company, state, end, transitions), kind, cap)

    def scenario(self, records=None, *, endpoint=Endpoint.OPERATING,
                 direction=Direction.OPTIMISTIC, horizon=8, cap=10, times=None,
                 policy=None):
        if records is None:
            records = [self.record()]
        if endpoint == Endpoint.SUCCESS and policy is None:
            policy = InitialPostPolicy.BASELINE_QUALIFIED
        return build_scenario(records, endpoint=endpoint, direction=direction,
                              horizon=horizon, extraction_limit=cap,
                              assignment_times={} if times is None else times,
                              initial_post_policy=policy)

    def test_all_six_endpoint_direction_contracts(self):
        for e in Endpoint:
            for d in Direction:
                event = (e == Endpoint.SUCCESS and d == Direction.OPTIMISTIC) or (
                    e != Endpoint.SUCCESS and d == Direction.ADVERSE)
                s = self.scenario(endpoint=e, direction=d, times={"a":5} if event else {})
                a = s.assignments[0]
                self.assertTrue(s.complete)
                self.assertEqual(a.original.observation_end, 2)
                self.assertEqual(a.original.transitions, ())
                self.assertEqual(len(a.hypothetical.transitions), int(event))
                self.assertEqual(a.hypothetical.observation_end,
                                 5 if event and e != Endpoint.SUCCESS else 8)
                if event:
                    self.assertEqual(a.hypothetical.transitions[0].destination,
                                     State.POST if e == Endpoint.SUCCESS else State.CLOSURE)
                self.assertIn("NOT_OBSERVED", s.interpretation)
                self.assertIn("NOT_IDENTIFICATION_BOUND", s.interpretation)

    def test_success_then_adverse_closure_preserves_known_success(self):
        tr = Transition(1, State.PRE, State.POST)
        r = self.record(transitions=(tr,))
        a = self.scenario([r], direction=Direction.ADVERSE, times={"a":6}).assignments[0]
        self.assertEqual(a.hypothetical.transitions,
                         (tr, Transition(6, State.POST, State.CLOSURE)))
        self.assertIs(a.original, r.history)

    def test_success_endpoint_already_determined_is_unchanged(self):
        for initial, transitions in [(State.POST,()),
            (State.PRE,(Transition(1,State.PRE,State.POST),))]:
            r = self.record(state=initial,transitions=transitions)
            for direction in Direction:
                s = self.scenario([r],endpoint=Endpoint.SUCCESS,direction=direction)
                self.assertTrue(s.complete)
                self.assertIs(s.assignments[0].original,s.assignments[0].hypothetical)
                self.assertEqual(s.assignments[0].status,"FIRST_SUCCESS_ALREADY_DETERMINED_UNCHANGED")

    def test_known_terminal_paths_and_later_history_are_preserved(self):
        for terminal in [State.CLOSURE,State.ACQUISITION_UNKNOWN,State.SUCCESS_EXIT]:
            r = self.record(end=3,cap=4,kind=FollowupKind.TERMINAL,
                            transitions=(Transition(3,State.PRE,terminal),))
            for e in Endpoint:
                for d in Direction:
                    s = self.scenario([r],endpoint=e,direction=d)
                    self.assertTrue(s.complete)
                    self.assertIs(s.assignments[0].hypothetical,r.history)
        future = self.record(end=10,cap=10,kind=FollowupKind.TERMINAL,
                            transitions=(Transition(9,State.PRE,State.CLOSURE),))
        a = self.scenario([future],direction=Direction.ADVERSE).assignments[0]
        self.assertIs(a.hypothetical,future.history)
        self.assertEqual(a.hypothetical.transitions[0].time,9)

    def test_admin_cap_not_reclassified_as_lost(self):
        r = self.record(end=3,cap=3,kind=FollowupKind.ADMINISTRATIVE)
        s = self.scenario([r])
        self.assertFalse(s.complete)
        self.assertEqual(s.assignments[0].status,"BLOCKED_HORIZON_BEYOND_ROUND_HARD_LIMIT")
        self.assertIs(s.assignments[0].hypothetical,r.history)

    def test_individual_cap_blocks_even_genuine_lost(self):
        s = self.scenario([self.record(cap=4)])
        self.assertFalse(s.complete)
        self.assertEqual(s.assignments[0].original,s.assignments[0].hypothetical)

    def test_mixed_packet_retains_blocked_rows_and_cannot_claim_complete(self):
        s = self.scenario([self.record(),self.record(name="b",end=3,cap=3,
                          kind=FollowupKind.ADMINISTRATIVE)])
        self.assertFalse(s.complete)
        self.assertEqual(len(s.assignments),2)
        self.assertEqual(s.assignments[0].status,"HYPOTHETICAL_TAIL_ASSIGNED")
        self.assertTrue(s.assignments[1].status.startswith("BLOCKED_"))

    def test_global_cap_rejects_future_even_all_terminal(self):
        r = self.record(end=1,kind=FollowupKind.TERMINAL,
                        transitions=(Transition(1,State.PRE,State.CLOSURE),))
        with self.assertRaisesRegex(ValueError,"beyond_hard_extraction"):
            self.scenario([r],horizon=11)

    def test_observation_at_horizon_has_no_missing_tail(self):
        r = self.record(end=8)
        s = self.scenario([r],direction=Direction.ADVERSE)
        self.assertTrue(s.complete)
        self.assertIs(s.assignments[0].hypothetical,r.history)

    def test_event_at_horizon_permitted(self):
        a = self.scenario(direction=Direction.ADVERSE,times={"a":8}).assignments[0]
        self.assertEqual(a.hypothetical.transitions[-1].time,8)

    def test_event_at_or_before_observed_time_or_after_horizon_rejected(self):
        for t in [0,1,2,8.0001,9]:
            with self.assertRaisesRegex(ValueError,"strictly_after_observation"):
                self.scenario(direction=Direction.ADVERSE,times={"a":t})

    def test_event_time_must_be_explicit(self):
        with self.assertRaisesRegex(ValueError,"explicit_hypothetical_event_time"):
            self.scenario(direction=Direction.ADVERSE)

    def test_unused_times_reject_silent_ignored_inputs(self):
        for times in [{"a":5},{"missing":5}]:
            with self.assertRaisesRegex(ValueError,"unused_or_ineligible"):
                self.scenario(times=times)
        with self.assertRaisesRegex(ValueError,"unused_or_ineligible"):
            self.scenario(direction=Direction.ADVERSE,times={"a":5,"unused":6})

    def test_terminal_initial_occupancy_preserved_success_held(self):
        for state in [State.CLOSURE,State.ACQUISITION_UNKNOWN,State.SUCCESS_EXIT]:
            r = self.record(state=state,end=0,kind=FollowupKind.TERMINAL)
            for endpoint in Endpoint:
                s = self.scenario([r],endpoint=endpoint)
                self.assertEqual(s.complete,endpoint!=Endpoint.SUCCESS)
                self.assertIs(s.assignments[0].hypothetical,r.history)

    def test_initial_post_requires_declared_success_semantics(self):
        s = self.scenario([self.record(state=State.POST)],endpoint=Endpoint.SUCCESS,
                          policy=InitialPostPolicy.REJECT)
        self.assertFalse(s.complete)
        with self.assertRaisesRegex(ValueError,"explicit_initial_post"):
            build_scenario([self.record()],endpoint=Endpoint.SUCCESS,
                           direction=Direction.OPTIMISTIC,horizon=8,extraction_limit=10,
                           assignment_times={"a":5})
        with self.assertRaisesRegex(ValueError,"applies_only"):
            self.scenario(policy=InitialPostPolicy.REJECT)

    def test_terminal_cannot_be_labeled_lost_or_admin(self):
        for kind in [FollowupKind.LOST,FollowupKind.ADMINISTRATIVE]:
            with self.assertRaisesRegex(ValueError,"conflicts_with_known_terminal"):
                self.scenario([self.record(kind=kind,transitions=(
                    Transition(1,State.PRE,State.CLOSURE),))])
        with self.assertRaisesRegex(ValueError,"conflicts_with_known_terminal"):
            self.scenario([self.record(kind=FollowupKind.TERMINAL)])

    def test_ambiguous_admin_and_loss_limits_rejected(self):
        with self.assertRaisesRegex(ValueError,"administrative_censor_must_equal"):
            self.scenario([self.record(kind=FollowupKind.ADMINISTRATIVE)])
        with self.assertRaisesRegex(ValueError,"lost_followup_requires_gap"):
            self.scenario([self.record(end=10)])

    def test_observation_cap_and_global_cap_order(self):
        for end,cap in [(5,4),(2,11)]:
            with self.assertRaisesRegex(ValueError,"hard_limits_inconsistent"):
                self.scenario([self.record(end=end,cap=cap)])

    def test_nonfinite_negative_boolean_huge_times_rejected(self):
        for value in [float("nan"),float("inf"),-1,True,10**1000,"5"]:
            for argument in ["horizon","cap"]:
                with self.assertRaises(ValueError):
                    self.scenario(**{argument:value})
            with self.assertRaises(ValueError):
                self.scenario(direction=Direction.ADVERSE,times={"a":value})
            with self.assertRaises(ValueError):
                self.scenario([self.record(cap=value)])

    def test_duplicates_empty_and_malformed_history_rejected(self):
        for records in [[],[self.record(),self.record()],
                        [self.record(transitions=(Transition(3,State.PRE,State.POST),))]]:
            with self.assertRaises(ValueError):
                self.scenario(records)

    def test_explicit_enums_and_mapping_required(self):
        for kw in [{"endpoint":"first_success"},{"direction":"optimistic"},
                   {"times":[]}, {"records":[self.record(kind="lost")]}]:
            with self.assertRaises(ValueError):
                self.scenario(**kw)

    def test_same_company_all_rounds_retained_without_coherence_claim(self):
        records = [self.record(name="a"),self.record(name="b",state=State.POST)]
        s = self.scenario(records,direction=Direction.ADVERSE,times={"a":3,"b":7})
        self.assertEqual([a.hypothetical.company_id for a in s.assignments],["co","co"])
        self.assertEqual(len(s.assignments),2)
        self.assertIn("ENDPOINT_LOCAL",s.interpretation)

    def test_randomized_prefix_immutability_and_hard_limits(self):
        rng = random.Random(13)
        for i in range(400):
            end = rng.uniform(1,3)
            horizon = rng.uniform(5,9)
            t = rng.uniform(end+.1,horizon)
            transition = (Transition(end/2,State.PRE,State.POST),) if i%2 else ()
            r = self.record(end=end,transitions=transition)
            original = r.history
            s = self.scenario([r],horizon=horizon,direction=Direction.ADVERSE,times={"a":t})
            h = s.assignments[0].hypothetical
            self.assertIs(s.assignments[0].original,original)
            self.assertEqual(h.transitions[:-1],original.transitions)
            self.assertEqual(h.initial_state,original.initial_state)
            self.assertLessEqual(h.observation_end,r.hard_limit)
            self.assertGreater(h.transitions[-1].time,original.observation_end)
            validate([h])


if __name__ == "__main__":
    unittest.main()
