# Testing Checklist

Final validation before production use.

## Setup (5 minutes)

### 1. Install Dependencies
```bash
cd /Users/grantgoldman/Documents/GitHub/content-accounts
pip3 install -r requirements.txt
```

Verify installation:
```bash
python3 -c "import questionary, rich, pydantic; print('✓ All dependencies installed')"
```

### 2. Check API Keys
```bash
# Verify .env file exists
cat .env

# Or check environment
echo $OPENROUTER_API_KEY
echo $GEMINI_API_KEY
```

## Test 1: Config Validation (2 minutes)

### Validate Migrated Account
```bash
python3 -m cli.validate dreamtimelullabies
```

**Expected output:**
```
✓ dreamtimelullabies
  Display: Dreamtime Lullabies
  Pillars: 36
  Colors: 6
  Output: /Users/grantgoldman/Google Drive/My Drive/DreamtimeLullabies
```

**Pass criteria:**
- [  ] No validation errors
- [  ] All 36 pillars present
- [  ] 6 color schemes shown
- [  ] Output path correct

## Test 2: Account Creation (30 minutes)

### Create Test Account via Wizard
```bash
python3 -m cli.create_account
```

**Configuration to use:**
- Account name: `testfitness`
- Template: Fitness
- Color palette: Energetic Brights
- Output: `/Users/grantgoldman/Documents/Content/testfitness`

**Pass criteria:**
- [  ] Wizard completes without errors
- [  ] All 9 steps work correctly
- [  ] Config files created in `accounts/testfitness/`
- [  ] 3 sample carousels generated
- [  ] Sample hook scores >= 12

### Verify Created Files
```bash
ls -la accounts/testfitness/
```

**Expected files:**
- [  ] `config.py`
- [  ] `scenes.json`
- [  ] `content_templates.json`
- [  ] `README.md`
- [  ] `.env` (if keys entered)

## Test 3: Content Generation (15 minutes)

### Test 1: Random Generation (dreamtimelullabies)
```bash
python3 -m cli.generate --account dreamtimelullabies --random
```

**Pass criteria:**
- [  ] Generates without errors
- [  ] Creates slides (5-10 PNG files)
- [  ] Creates caption.txt
- [  ] Creates meta.json
- [  ] Hook score >= 12 (check logs)
- [  ] Images have text overlays
- [  ] Output in Google Drive directory

### Test 2: Specific Topic (testfitness)
```bash
python3 -m cli.generate --account testfitness --topic "leg day workout routine"
```

**Pass criteria:**
- [  ] Auto-selects appropriate format
- [  ] Generates 5 slides
- [  ] Content relevant to topic
- [  ] Hashtags match fitness niche

### Test 3: Custom Format
```bash
python3 -m cli.generate --account testfitness --topic "warmup stretches" --format step_guide --slides 7
```

**Pass criteria:**
- [  ] Uses step_guide format
- [  ] Creates 7 slides (hook + 5 steps + CTA)
- [  ] Steps numbered correctly

### Test 4: Batch Generation
```bash
python3 -m cli.generate --account testfitness --random --count 3
```

**Pass criteria:**
- [  ] Generates 3 separate carousels
- [  ] All 3 complete successfully
- [  ] Different topics for each
- [  ] No duplicate content

## Test 4: Quality Verification (20 minutes)

### Check Hook Scores
Review generated carousels and verify:

**Scoring criteria (20-point system):**
- [  ] Curiosity gap (1-5 points)
- [  ] Actionability (1-5 points)
- [  ] Specificity (1-5 points)
- [  ] Scroll stop (1-5 points)

**Pass threshold:** >= 12 points (Grade B)

### Check Visual Quality
For each generated carousel:
- [  ] Slides are 1080x1920 (9:16 ratio)
- [  ] Text is readable
- [  ] Emojis render correctly
- [  ] No text clipping
- [  ] Images darken appropriately
- [  ] Hook slide has dramatic effect

### Check Content Quality
- [  ] Lowercase (except "I")
- [  ] Conversational tone
- [  ] No quotation marks
- [  ] No meta-text artifacts
- [  ] CTA matches brand

## Test 5: Comparison (30 minutes)

### Generate with Old System
```bash
cd /Users/grantgoldman/Documents/GitHub/dreamtimelullabies
python3 dreamtime.py --random --count 3
```

### Generate with New System
```bash
cd /Users/grantgoldman/Documents/GitHub/content-accounts
python3 -m cli.generate --account dreamtimelullabies --random --count 3
```

### Compare Outputs
- [  ] Hook quality equivalent
- [  ] Slide formatting identical
- [  ] Image prompts similar quality
- [  ] Caption format matches
- [  ] Hashtags identical
- [  ] Directory structure same

## Test 6: Edge Cases (15 minutes)

### Test Invalid Inputs
```bash
# Missing account
python3 -m cli.generate --account nonexistent --random
# Expected: Clear error message

# Invalid slide count
python3 -m cli.generate --account testfitness --random --slides 20
# Expected: Validation error (must be 5-10)

# No topic or random
python3 -m cli.generate --account testfitness
# Expected: Error requiring topic or --random
```

**Pass criteria:**
- [  ] All errors caught gracefully
- [  ] Clear error messages
- [  ] No stack traces (unless --verbose)

## Test 7: Performance (10 minutes)

### Measure Generation Time
```bash
time python3 -m cli.generate --account testfitness --random
```

**Expected performance:**
- Text generation: 10-30 seconds
- Image generation: 30-60 seconds per slide
- **Total per carousel: 3-5 minutes**

### Measure Batch Performance
```bash
time python3 -m cli.generate --account testfitness --random --count 5
```

**Pass criteria:**
- [  ] Completes in reasonable time (~15-25 mins for 5)
- [  ] No memory issues
- [  ] No API rate limit errors

## Test 8: Multi-Account (15 minutes)

### Create Second Test Account
```bash
python3 -m cli.create_account
```

Use different template:
- Account: `testcooking`
- Template: Cooking
- Colors: Warm Neutrals

### Generate from Both Accounts
```bash
python3 -m cli.generate --account testfitness --random
python3 -m cli.generate --account testcooking --random
```

**Pass criteria:**
- [  ] Each account uses own config
- [  ] No cross-contamination
- [  ] Output to correct directories
- [  ] Different brand voices
- [  ] Different hashtags

### Validate All Accounts
```bash
python3 -m cli.validate --all
```

**Expected output:**
```
✓ dreamtimelullabies
✓ testfitness
✓ testcooking

Results: 3 passed, 0 failed
```

## Summary Checklist

### Core Functionality
- [  ] Config validation works
- [  ] Account creation wizard works
- [  ] Content generation works
- [  ] Templates load correctly
- [  ] API integrations work (Claude + Gemini)

### Quality
- [  ] Hook scores >= 12
- [  ] Slides render correctly
- [  ] Content matches brand voice
- [  ] Images appropriate quality
- [  ] Captions formatted properly

### Framework Features
- [  ] Multiple accounts work independently
- [  ] Shared core library (no duplication)
- [  ] Config validation catches errors
- [  ] Migration preserved functionality
- [  ] CLI tools work correctly

### Documentation
- [  ] README clear and complete
- [  ] QUICK_START usable
- [  ] COMPLETION_SUMMARY accurate
- [  ] Example outputs generated

## Known Issues / Notes

Document any issues found during testing:

**Issue 1:**
- Description:
- Impact:
- Workaround:

**Issue 2:**
- Description:
- Impact:
- Workaround:

## Sign-Off

**Tester:** _______________
**Date:** _______________
**Status:** [ ] Pass  [ ] Pass with notes  [ ] Fail

**Notes:**

---

## If All Tests Pass

The framework is production-ready! 🚀

**Next steps:**
1. Archive old dreamtimelullabies repo
2. Create production accounts
3. Set up monitoring for quality metrics
4. Document any customizations
5. Share framework with team

## If Issues Found

1. Document issues in "Known Issues" section
2. Prioritize by impact
3. Fix critical issues
4. Re-run affected tests
5. Update documentation as needed
